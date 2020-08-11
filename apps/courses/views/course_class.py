import datetime
import os
from typing import Optional

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import CreateView, UpdateView, DeleteView

from core.exceptions import Redirect
from core.urls import reverse, reverse_lazy
from core.utils import hashids
from core.views import ProtectedFormMixin
from courses.forms import CourseClassForm
from courses.models import CourseClass, CourseClassAttachment
from courses.permissions import ViewCourseClassAttachment, \
    ViewCourseClassMaterials
from courses.views.mixins import CourseURLParamsMixin
from files.views import ProtectedFileDownloadView
from users.mixins import TeacherOnlyMixin

__all__ = ('CourseClassDetailView', 'CourseClassCreateView',
           'CourseClassUpdateView', 'CourseClassDeleteView',
           'CourseClassAttachmentDeleteView')


class CourseClassDetailView(generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'
    template_name = "courses/course_class_detail.html"

    def get_queryset(self):
        return (CourseClass.objects
                .select_related("course",
                                "course__meta_course",
                                "course__main_branch",
                                "course__semester",
                                "venue",
                                "venue__location",))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attachments'] = self.object.courseclassattachment_set.all()
        return context


class CourseClassCreateUpdateMixin(CourseURLParamsMixin):
    def get_form(self, **kwargs):
        course = self.course
        if not self.is_form_allowed(self.request.user, course):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = course
        kwargs["initial"] = self.get_initial(**kwargs)
        return CourseClassForm(**kwargs)

    @staticmethod
    def is_form_allowed(user, course):
        return user.is_curator or user in course.teachers.all()

    def get_initial(self, **kwargs):
        return None

    # TODO: add atomic
    def form_valid(self, form):
        self.object = form.save()
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                CourseClassAttachment(course_class=self.object,
                                      material=attachment).save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return_url = self.request.GET.get('back')
        if return_url == 'timetable':
            return reverse('teaching:timetable')
        if return_url == 'course':
            return self.object.course.get_absolute_url()
        if return_url == 'calendar':
            return reverse('teaching:calendar')
        elif "_addanother" in self.request.POST:
            return self.object.course.get_create_class_url()
        else:
            return super().get_success_url()


class CourseClassCreateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin, CreateView):
    model = CourseClass
    template_name = "lms/courses/course_class_form.html"

    def get_initial(self, **kwargs):
        course = kwargs["course"]
        initial = {
            "materials_visibility": course.materials_visibility
        }
        # TODO: Add tests for initial data after discussion
        previous_class = (CourseClass.objects
                          .filter(course=course.pk)
                          .defer("description")
                          .order_by("-date", "starts_at")
                          .first())
        if previous_class is not None:
            initial.update({
                "type": previous_class.type,
                "venue": previous_class.venue,
                "starts_at": previous_class.starts_at,
                "ends_at": previous_class.ends_at,
                "date": previous_class.date + datetime.timedelta(weeks=1)
            })
        return initial

    def get_success_url(self):
        msg = _("The class '%s' was successfully created.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super().get_success_url()

    def post(self, request, *args, **kwargs):
        """Teacher can't add new class if course already completed"""
        course = self.course
        if not self.request.user.is_curator and course.is_completed:
            return HttpResponseForbidden()
        form = self.get_form(data=request.POST, files=request.FILES,
                             course=course)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class CourseClassUpdateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin, UpdateView):
    model = CourseClass
    template_name = "lms/courses/course_class_form.html"

    def get_success_url(self):
        msg = _("The class '%s' was successfully updated.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super().get_success_url()


class CourseClassDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                            DeleteView):
    model = CourseClass
    template_name = "forms/simple_delete_confirmation.html"
    success_url = reverse_lazy('teaching:timetable')

    def is_form_allowed(self, user, obj: CourseClass):
        return user.is_curator or user in obj.course.teachers.all()


class CourseClassAttachmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                      DeleteView):
    model = CourseClassAttachment
    template_name = "forms/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_curator or
                user in obj.course_class.course.teachers.all())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        # TODO: move to model method
        # FIXME: remove with storage only
        os.remove(self.object.material.path)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.object.course_class.get_update_url()


class CourseClassAttachmentDownloadView(ProtectedFileDownloadView):
    permission_required = ViewCourseClassAttachment.name
    file_field_name = 'material'

    def get_protected_object(self) -> Optional[CourseClassAttachment]:
        ids: tuple = hashids.decode(self.kwargs['sid'])
        if not ids:
            raise Http404
        qs = (CourseClassAttachment.objects
              .filter(pk=ids[0])
              .select_related('course_class__course'))
        return get_object_or_404(qs)


class CourseClassSlidesDownloadView(ProtectedFileDownloadView):
    permission_required = ViewCourseClassMaterials.name
    file_field_name = 'slides'

    def get_protected_object(self) -> Optional[CourseClass]:
        ids: tuple = hashids.decode(self.kwargs['sid'])
        if not ids:
            raise Http404
        qs = (CourseClass.objects
              .filter(pk=ids[0])
              .select_related('course'))
        return get_object_or_404(qs)
