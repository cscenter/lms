from typing import Any, Optional

from vanilla import DeleteView

from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic.base import TemplateResponseMixin

from auth.mixins import PermissionRequiredMixin
from core.http import AuthenticatedHttpRequest, HttpRequest
from core.urls import reverse
from courses.constants import AssigneeMode, AssignmentFormat
from courses.forms import (
    AssignmentForm, AssignmentResponsibleTeachersFormFactory,
    StudentGroupAssigneeFormFactory
)
from courses.models import Assignment, AssignmentAttachment, Course, CourseGroupModes
from courses.permissions import (
    CreateAssignment, DeleteAssignment, DeleteAssignmentAttachment, EditAssignment
)
from courses.views.mixins import CourseURLParamsMixin
from learning.services import AssignmentService, StudentGroupService

__all__ = ('AssignmentCreateView', 'AssignmentUpdateView',
           'AssignmentDeleteView', 'AssignmentAttachmentDeleteView')


def _get_assignment_form(course: Course, request: HttpRequest,
                         assignment: Optional[Assignment] = None):
    form_kwargs = {
        'course': course,
        'locale': request.LANGUAGE_CODE,
        'instance': assignment
    }
    if course.group_mode == CourseGroupModes.MANUAL:
        default_mode = AssigneeMode.STUDENT_GROUP_DEFAULT
    else:
        default_mode = AssigneeMode.MANUAL
    if request.method == 'GET' and assignment is None:
        form_kwargs["initial"] = {
            "assignee_mode": default_mode,
            "time_zone": course.main_branch.get_timezone() or None
        }
    if request.method == 'POST':
        form_kwargs.update({
            'data': request.POST,
            'files': request.FILES
        })
    return AssignmentForm(**form_kwargs)


class AssignmentCreateUpdateBaseView(CourseURLParamsMixin, PermissionRequiredMixin,
                                     TemplateResponseMixin, View):
    request: AuthenticatedHttpRequest

    def get(self, request: AuthenticatedHttpRequest, *args: Any, **kwargs: Any):
        return self._handle_request(request)

    def post(self, request: AuthenticatedHttpRequest, *args: Any, **kwargs: Any):
        return self._handle_request(request)

    def _handle_request(self, request: AuthenticatedHttpRequest):
        assignment = self.get_object()
        post_data = request.POST if request.method == 'POST' else None
        assignment_form = _get_assignment_form(self.course, request, assignment=assignment)
        selected_assignee_mode = assignment_form['assignee_mode'].value()
        responsible_teachers_form = AssignmentResponsibleTeachersFormFactory.build_form(
            self.course, assignment=assignment,
            data=post_data)
        student_groups_custom_form = StudentGroupAssigneeFormFactory.build_form(
            self.course, is_required=(selected_assignee_mode == AssigneeMode.STUDENT_GROUP_CUSTOM),
            assignment=assignment, data=post_data)
        all_forms = [
            assignment_form,
            responsible_teachers_form,
            student_groups_custom_form
        ]
        if request.method == 'POST' and self.all_valid(*all_forms):
            return self.save(*all_forms)
        context = {
            "AssigneeMode": AssigneeMode,
            "formats_with_checker": AssignmentFormat.with_checker,
            "assignment_form": assignment_form,
            "responsible_teachers_form": responsible_teachers_form,
            "student_groups_custom_form": student_groups_custom_form,
        }
        return self.render_to_response(context)

    @staticmethod
    def all_valid(assignment_form, responsible_teachers_form, student_groups_custom_form):
        selected_assignee_mode = assignment_form['assignee_mode'].value()
        to_validate = [assignment_form]
        if selected_assignee_mode == AssigneeMode.MANUAL:
            to_validate.append(responsible_teachers_form)
        elif selected_assignee_mode == AssigneeMode.STUDENT_GROUP_CUSTOM:
            to_validate.append(student_groups_custom_form)
        return all(f.is_valid() for f in to_validate)

    def get_object(self) -> Optional[Assignment]:
        raise NotImplementedError

    def save(self, *args, **kwargs):
        raise NotImplementedError


class AssignmentCreateView(AssignmentCreateUpdateBaseView):
    permission_required = CreateAssignment.name
    template_name = "lms/courses/course_assignment_form.html"

    def get_permission_object(self) -> Course:
        return self.course

    def get_object(self) -> Optional[Assignment]:
        return None

    def save(self, assignment_form, responsible_teachers_form, student_groups_custom_form):
        attachments = self.request.FILES.getlist('assignment-attachments')
        with transaction.atomic(savepoint=False):
            assignment = assignment_form.save()
            AssignmentService.bulk_create_student_assignments(assignment)
            if assignment.assignee_mode == AssigneeMode.MANUAL:
                data = responsible_teachers_form.to_internal()
                AssignmentService.set_responsible_teachers(assignment,
                                                           teachers=data['responsible_teachers'])
            elif assignment.assignee_mode == AssigneeMode.STUDENT_GROUP_CUSTOM:
                data = student_groups_custom_form.to_internal()
                StudentGroupService.set_custom_assignees_for_assignment(assignment=assignment, data=data)
            AssignmentService.process_attachments(assignment, attachments)
        return redirect(assignment.get_teacher_url())


class AssignmentUpdateView(AssignmentCreateUpdateBaseView):
    assignment: Assignment
    permission_required = EditAssignment.name
    template_name = "lms/courses/course_assignment_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        queryset = (Assignment.objects
                    .filter(pk=kwargs['pk'], course=self.course))
        self.assignment = get_object_or_404(queryset)

    def get_permission_object(self) -> Assignment:
        return self.assignment

    def get_object(self) -> Assignment:
        return self.assignment

    def save(self, assignment_form, responsible_teachers_form, student_groups_custom_form):
        attachments = self.request.FILES.getlist('assignment-attachments')
        with transaction.atomic(savepoint=False):
            assignment = assignment_form.save()
            if assignment.assignee_mode == AssigneeMode.MANUAL:
                data = responsible_teachers_form.to_internal()
                AssignmentService.set_responsible_teachers(assignment, teachers=data['responsible_teachers'])
                # TODO: track .assignee_mode to cleanup previous settings on change
            elif assignment.assignee_mode == AssigneeMode.STUDENT_GROUP_CUSTOM:
                data = student_groups_custom_form.to_internal()
                StudentGroupService.set_custom_assignees_for_assignment(assignment=assignment, data=data)
            # TODO: Call this one only if .restricted_to has changed
            AssignmentService.sync_student_assignments(assignment)
            AssignmentService.process_attachments(assignment, attachments)
        return redirect(assignment.get_teacher_url())


class AssignmentDeleteView(PermissionRequiredMixin, CourseURLParamsMixin, DeleteView):
    template_name = "forms/simple_delete_confirmation.html"
    permission_required = DeleteAssignment.name
    assignment: Assignment

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (Assignment.objects
                    .filter(pk=kwargs['pk'],
                            course=self.course))
        self.assignment = get_object_or_404(queryset)
        self.assignment.course = self.course

    def get_success_url(self):
        return reverse('teaching:assignments_check_queue')

    def get_permission_object(self):
        return self.assignment

    def get_object(self):
        return self.assignment


class AssignmentAttachmentDeleteView(PermissionRequiredMixin, CourseURLParamsMixin, DeleteView):
    template_name = "forms/simple_delete_confirmation.html"
    permission_required = DeleteAssignmentAttachment.name
    attachment: AssignmentAttachment

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (AssignmentAttachment.objects
                    .filter(pk=kwargs['pk'],
                            assignment__course=self.course)
                    .select_related('assignment'))
        self.attachment = get_object_or_404(queryset)
        self.attachment.assignment.course = self.course

    def get_success_url(self):
        return self.object.assignment.get_update_url()

    def get_permission_object(self):
        return self.attachment

    def get_object(self):
        return self.attachment
