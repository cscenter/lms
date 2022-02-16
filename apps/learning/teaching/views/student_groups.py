from typing import Any

from vanilla import CreateView, DeleteView, DetailView, ListView, UpdateView

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from auth.mixins import PermissionRequiredMixin
from core.http import AuthenticatedHttpRequest, HttpRequest
from courses.models import StudentGroupTypes
from courses.views.mixins import CourseURLParamsMixin
from learning.models import StudentGroup, StudentGroupAssignee
from learning.permissions import (
    CreateStudentGroup, DeleteStudentGroup, UpdateStudentGroup, ViewStudentGroup
)
from learning.services import StudentGroupService
from learning.teaching.forms import StudentGroupForm, StudentGroupStudentsTransferForm
from learning.teaching.utils import get_create_student_group_url, get_student_groups_url


class StudentGroupListView(PermissionRequiredMixin, CourseURLParamsMixin, ListView):
    template_name = "lms/teaching/student_groups/student_group_list.html"
    permission_required = ViewStudentGroup.name

    def get_permission_object(self):
        return self.course

    def get(self, request: AuthenticatedHttpRequest, *args: Any, **kwargs: Any):
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        student_groups = self.get_queryset()
        for student_group in student_groups:
            # Avoids additional db hits on building friendly URL
            student_group.course = self.course
        context = {
            'course': self.course,
            'student_group_list': student_groups,
            'get_create_student_group_url': get_create_student_group_url,
            'permissions': {
                'create_student_group': CreateStudentGroup.name
            }
        }
        return context

    def get_queryset(self):
        # TODO: move to selectors
        student_group_assignees = Prefetch(
            'student_group_assignees',
            queryset=StudentGroupAssignee.objects.select_related('assignee__teacher')
        )
        return (StudentGroup.objects
                .filter(course=self.course)
                .select_related('branch__site')
                .prefetch_related(student_group_assignees)
                .order_by('name'))


class StudentGroupDetailView(PermissionRequiredMixin, CourseURLParamsMixin, DetailView):
    template_name = "lms/teaching/student_groups/student_group_detail.html"
    permission_required = ViewStudentGroup.name

    def get_permission_object(self):
        return self.course

    def get(self, request, *args, **kwargs):
        queryset = (StudentGroup.objects
                    .filter(pk=kwargs['pk'],
                            course=self.course))
        student_group = get_object_or_404(queryset)
        student_group.course = self.course
        context = self.get_context_data(student_group=student_group)
        return self.render_to_response(context)

    def get_context_data(self, student_group: StudentGroup, **kwargs):
        context = {
            'course': self.course,
            'student_group': student_group,
            'assigned_teachers': StudentGroupService.get_assignees(student_group),
            'enrollments': StudentGroupService.get_enrollments(student_group),
            'get_student_groups_url': get_student_groups_url,
            'permissions': {
                'update_student_group': UpdateStudentGroup.name,
                'delete_student_group': DeleteStudentGroup.name
            }
        }
        return context


class StudentGroupCreateView(PermissionRequiredMixin, CourseURLParamsMixin, CreateView):
    template_name = "lms/teaching/student_groups/student_group_create.html"
    permission_required = CreateStudentGroup.name

    def get_permission_object(self):
        return self.course

    def get_form(self, data=None, files=None, **kwargs):
        return StudentGroupForm(self.course, data=data, files=files, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            student_group = StudentGroupService.create(self.course,
                                                       group_type=StudentGroupTypes.MANUAL,
                                                       name=form.cleaned_data['name'])
            assignee = form.cleaned_data.get('assignee')
            if assignee:
                StudentGroupService.add_assignees(student_group, teachers=[assignee])
        redirect_to = get_student_groups_url(self.course)
        return HttpResponseRedirect(redirect_to)


class StudentGroupUpdateView(PermissionRequiredMixin, CourseURLParamsMixin, UpdateView):
    template_name = "lms/teaching/student_groups/student_group_update.html"
    permission_required = UpdateStudentGroup.name
    student_group: StudentGroup

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (StudentGroup.objects
                    .filter(pk=kwargs['pk'],
                            course=self.course))
        self.student_group = get_object_or_404(queryset)
        self.student_group.course = self.course

    def get_permission_object(self):
        return self.student_group

    def get_object(self):
        return self.student_group

    def get_form(self, data=None, files=None, **kwargs):
        responsible_teachers = StudentGroupService.get_assignees(self.student_group)
        if responsible_teachers:
            kwargs["initial"] = {"assignee": responsible_teachers[0]}
        return StudentGroupForm(self.course, data=data, files=files, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            student_group = self.student_group
            StudentGroupService.update(student_group, name=form.cleaned_data['name'])
            assignee = form.cleaned_data.get('assignee')
            responsible_teachers = [assignee] if assignee else []
            StudentGroupService.update_assignees(student_group,
                                                 teachers=responsible_teachers)
        redirect_to = self.student_group.get_absolute_url()
        return HttpResponseRedirect(redirect_to)

    def get_context_data(self, **kwargs: Any):
        context = {
            'transfer_form': StudentGroupStudentsTransferForm(self.student_group),
            'enrollments': StudentGroupService.get_enrollments(self.student_group),
            **kwargs
        }
        return context


class StudentGroupDeleteView(PermissionRequiredMixin, CourseURLParamsMixin, DeleteView):
    template_name = "lms/teaching/student_groups/student_group_delete.html"
    permission_required = DeleteStudentGroup.name
    student_group: StudentGroup

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (StudentGroup.objects
                    .filter(pk=kwargs['pk'],
                            course=self.course))
        self.student_group = get_object_or_404(queryset)
        self.student_group.course = self.course

    def get_permission_object(self):
        return self.student_group

    def get_object(self):
        return self.student_group

    def get_context_data(self, **kwargs):
        context = {"student_group": self.student_group}
        return context

    def post(self, request, *args, **kwargs):
        student_group = self.get_object()
        try:
            StudentGroupService.remove(student_group)
        except ValidationError as e:
            messages.error(request, str(e))
        redirect_to = get_student_groups_url(self.course)
        return HttpResponseRedirect(redirect_to)
