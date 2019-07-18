import os

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from vanilla import CreateView, UpdateView, DeleteView

from core.exceptions import Redirect
from core.urls import reverse
from core.views import ProtectedFormMixin
from courses.forms import AssignmentForm
from courses.models import Assignment, Course, AssignmentAttachment
from courses.views.mixins import CourseURLParamsMixin
from users.mixins import TeacherOnlyMixin

__all__ = ('AssignmentCreateView', 'AssignmentUpdateView',
           'AssignmentDeleteView', 'AssignmentAttachmentDeleteView')


class AssignmentCreateUpdateMixin(TeacherOnlyMixin, CourseURLParamsMixin):
    model = Assignment
    form_class = AssignmentForm
    template_name = "courses/course_assignment_form.html"

    def get_form(self, **kwargs):
        course = self.course
        if not self.is_form_allowed(self.request.user, course):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = course
        return AssignmentForm(**kwargs)

    @staticmethod
    def is_form_allowed(user, course: Course):
        return user.is_curator or user in course.teachers.all()

    def get_success_url(self):
        return self.object.get_teacher_url()

    # TODO: Add atomic
    def form_valid(self, form):
        self.save_form(form)
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                (AssignmentAttachment.objects
                 .create(assignment=self.object, attachment=attachment))
        return redirect(self.get_success_url())

    def save_form(self, form):
        raise NotImplementedError()


class AssignmentCreateView(AssignmentCreateUpdateMixin, CreateView):
    def save_form(self, form):
        self.object = form.save()
        # Set up notifications recipients setting
        course = self.object.course
        co_teachers = course.course_teachers.all()
        notify_teachers = [t.pk for t in co_teachers if t.notify_by_default]
        self.object.notify_teachers.add(*notify_teachers)


class AssignmentUpdateView(AssignmentCreateUpdateMixin, UpdateView):
    def save_form(self, form):
        self.object = form.save()


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
        os.remove(self.object.attachment.path)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.object.assignment.get_update_url()
