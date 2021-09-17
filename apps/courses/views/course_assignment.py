from typing import TYPE_CHECKING, Any, Dict

from vanilla import CreateView, DeleteView, UpdateView

from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect

from auth.mixins import PermissionRequiredMixin
from core.urls import reverse
from core.views import ProtectedFormMixin
from courses.constants import AssignmentFormat
from courses.forms import AssignmentForm
from courses.models import Assignment, AssignmentAttachment, Course
from courses.permissions import CreateAssignment, EditAssignment
from courses.views.mixins import CourseURLParamsMixin
from learning.services import AssignmentService
from users.mixins import TeacherOnlyMixin

__all__ = ('AssignmentCreateView', 'AssignmentUpdateView',
           'AssignmentDeleteView', 'AssignmentAttachmentDeleteView')


if TYPE_CHECKING:
    from vanilla import GenericModelView
    AssignmentCreateUpdateMixinBase = GenericModelView
else:
    AssignmentCreateUpdateMixinBase = object


class AssignmentCreateUpdateMixin(CourseURLParamsMixin, PermissionRequiredMixin,
                                  AssignmentCreateUpdateMixinBase):
    model = Assignment
    template_name = "lms/courses/course_assignment_form.html"

    def get_form(self, **kwargs):
        return AssignmentForm(course=self.course,
                              locale=self.request.LANGUAGE_CODE,
                              **kwargs)

    def get_success_url(self):
        return self.object.get_teacher_url()

    def form_valid(self, form):
        attachments = self.request.FILES.getlist('attachments')
        with transaction.atomic(savepoint=False):
            self.object = form.save()
            self.post_save(self.object)
            AssignmentService.process_attachments(self.object, attachments)
        return redirect(self.get_success_url())

    def post_save(self, form):
        pass

    def get_context_data(self, form: AssignmentForm, **kwargs: Any) -> Dict[str, Any]:
        context = {
            "form": form,
            "formats_with_checker": AssignmentFormat.with_checker
        }
        return context


class AssignmentCreateView(AssignmentCreateUpdateMixin, CreateView):
    permission_required = CreateAssignment.name

    def get_permission_object(self) -> Course:
        return self.course

    def get_form(self, **kwargs):
        kwargs['initial'] = {
            "time_zone": self.course.main_branch.get_timezone() or None
        }
        return super().get_form(**kwargs)

    def post_save(self, assignment):
        AssignmentService.bulk_create_student_assignments(assignment)
        AssignmentService.setup_assignees(assignment)


class AssignmentUpdateView(AssignmentCreateUpdateMixin, UpdateView):
    assignment: Assignment
    permission_required = EditAssignment.name

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        queryset = (Assignment.objects
                    .filter(pk=kwargs['pk'], course=self.course))
        self.assignment = get_object_or_404(queryset)

    def get_permission_object(self) -> Assignment:
        return self.assignment

    def post_save(self, assignment):
        AssignmentService.sync_student_assignments(assignment)


class AssignmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin, DeleteView):
    model = Assignment
    template_name = "forms/simple_delete_confirmation.html"

    def get_success_url(self):
        return reverse('teaching:assignment_list')

    def is_form_allowed(self, user, obj: Assignment):
        return user.is_curator or user in obj.course.teachers.all()


class AssignmentAttachmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                     DeleteView):
    model = AssignmentAttachment
    template_name = "forms/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_curator or
                user in obj.assignment.course.teachers.all())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        self.object.attachment.delete(save=False)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.object.assignment.get_update_url()
