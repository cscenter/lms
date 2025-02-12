import datetime
from typing import TYPE_CHECKING, Any, Optional

from django.forms import ValidationError
from vanilla import CreateView, DeleteView, UpdateView

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.http import HttpRequest
from core.urls import reverse, reverse_lazy
from core.utils import hashids
from courses.forms import CourseClassForm
from courses.models import CourseClass, CourseClassAttachment
from courses.permissions import (
    CreateCourseClass, DeleteCourseClass, EditCourseClass, ViewCourse, ViewCourseClassMaterials
)
from courses.views.mixins import CourseURLParamsMixin
from files.views import ProtectedFileDownloadView

__all__ = ('CourseClassDetailView', 'CourseClassCreateView',
           'CourseClassUpdateView', 'CourseClassDeleteView',
           'CourseClassAttachmentDeleteView')


if TYPE_CHECKING:
    from django.views import View
    CourseClassURLParamsBase = View
    CourseClassFormMixinBase = View
else:
    CourseClassURLParamsBase = object
    CourseClassFormMixinBase = object


class CourseClassDetailView(CourseURLParamsMixin, PermissionRequiredMixin, generic.DetailView):
    model = CourseClass
    permission_required = ViewCourse.name
    context_object_name = 'course_class'
    template_name = "lms/courses/course_class_detail.html"
    
    def get_permission_object(self):
        return self.course

    def get_queryset(self):
        url_params = self.kwargs
        # FIXME: check course is available on current site
        return (CourseClass.objects
                .filter(course_id=url_params['course_id'])
                .select_related("course",
                                "course__meta_course",
                                "course__main_branch",
                                "course__semester",
                                "venue",
                                "venue__location",))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attachments'] = self.object.courseclassattachment_set.order_by("-created")
        return context


class CourseClassURLParamsMixin(CourseURLParamsMixin, CourseClassURLParamsBase):
    course_class: CourseClass

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (CourseClass.objects
                    .filter(pk=kwargs['pk'],
                            course=self.course)
                    .select_related('course'))
        self.course_class = get_object_or_404(queryset)


class CourseClassFormMixin(CourseClassFormMixinBase):
    def get_form(self, **kwargs):
        course = self.course
        if not self.request.user.has_perm(CreateCourseClass.name, course):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = course
        kwargs["initial"] = self.get_initial(**kwargs)
        return CourseClassForm(locale=self.request.LANGUAGE_CODE, **kwargs)

    def get_initial(self, **kwargs):
        return None


    def get_success_url(self, to_classes_list=False):
        return_url = self.request.GET.get('back')
        if return_url == 'timetable':
            return reverse('teaching:timetable')
        if return_url == 'course':
            return self.object.course.get_absolute_url()
        if return_url == 'calendar':
            return reverse('teaching:calendar')
        elif "_addanother" in self.request.POST:
            return self.object.course.get_create_class_url()
        elif to_classes_list:
            return self.object.course.get_url_for_tab("classes")
        else:
            return super().get_success_url()


class CourseClassCreateView(PermissionRequiredMixin, CourseURLParamsMixin,
                            CourseClassFormMixin, CreateView):
    model = CourseClass
    permission_required = CreateCourseClass.name
    template_name = "lms/courses/course_class_form.html"

    def get_permission_object(self):
        return self.course

    def get_initial(self, **kwargs):
        course = kwargs["course"]
        initial = {
            "materials_visibility": course.materials_visibility,
            "translation_link": course.translation_link,
            "time_zone": course.main_branch.get_timezone() or None
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
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                number_of_repeats = form.cleaned_data.pop('number_of_repeats') or 1
                is_repeated = form.cleaned_data.pop('is_repeated')
                if number_of_repeats != 1 and not is_repeated:
                    raise ValidationError(_("Form error. is_repeated is False and number_of_repeats is not 1"))
                base_name = form.cleaned_data.get('name')
                base_date = form.cleaned_data.get('date')
                
                for i in range(number_of_repeats):
                    self.object = form.save(commit=False)
                    self.object.name = base_name if i == 0 else f"{base_name} #{i+1}" 
                    self.object.date = base_date + datetime.timedelta(weeks=i) 
                    self.object.pk = None # Ensure a new object is created
                    self.object.save()

                    attachments = self.request.FILES.getlist('attachments')
                    if attachments:
                        for attachment in attachments:
                            CourseClassAttachment.objects.create(course_class=self.object, material=attachment)
                
                return redirect(self.get_success_url(number_of_repeats != 1, base_name, base_date))
                
        except Exception as e:
            messages.error(self.request, _("Class creation error: {exception}")).format(exception=str(e))
            return self.form_invalid(form)

    def get_success_url(self, is_repeated=False, name=None, date=None):
        if not is_repeated:
            msg = _('The class "{name}" was successfully created.').format(name=self.object.name)
        else:
            msg = _('The classes "{name}" from {from_date} to {to_date} were successfully created.').format(
                name=name,
                from_date=date,
                to_date=self.object.date)
        messages.success(self.request, msg, extra_tags='timeout')
        return super().get_success_url(to_classes_list=is_repeated)

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


class CourseClassUpdateView(PermissionRequiredMixin, CourseClassURLParamsMixin,
                            CourseClassFormMixin, UpdateView):
    model = CourseClass
    permission_required = EditCourseClass.name
    template_name = "lms/courses/course_class_form.html"

    def get_permission_object(self):
        return self.course_class

    def get_object(self):
        return self.course_class
    
    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            attachments = self.request.FILES.getlist('attachments')
            if attachments:
                for attachment in attachments:
                    CourseClassAttachment(course_class=self.object,
                                        material=attachment).save()
            return redirect(self.get_success_url())

    def get_success_url(self):
        msg = _("The class '%s' was successfully updated.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super().get_success_url()


class CourseClassDeleteView(PermissionRequiredMixin, CourseClassURLParamsMixin,
                            DeleteView):
    model = CourseClass
    permission_required = DeleteCourseClass.name
    template_name = "forms/simple_delete_confirmation.html"
    success_url = reverse_lazy('teaching:timetable')

    def get_permission_object(self):
        return self.course_class


class CourseClassAttachmentDeleteView(PermissionRequiredMixin, DeleteView):
    model = CourseClassAttachment
    permission_required = EditCourseClass.name
    template_name = "forms/simple_delete_confirmation.html"
    attachment: CourseClassAttachment

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        attachment_queryset = (CourseClassAttachment.objects
                               .filter(pk=kwargs['pk'])
                               .select_related('course_class__course'))
        self.attachment = get_object_or_404(attachment_queryset)

    def get_permission_object(self):
        return self.attachment.course_class

    def get_object(self):
        return self.attachment

    def post(self, request, *args, **kwargs):
        self.attachment.delete()
        self.attachment.material.delete(save=False)
        redirect_to = self.attachment.course_class.get_update_url()
        return HttpResponseRedirect(redirect_to)


class CourseClassAttachmentDownloadView(ProtectedFileDownloadView):
    permission_required = ViewCourseClassMaterials.name
    file_field_name = 'material'

    def get_protected_object(self) -> Optional[CourseClassAttachment]:
        ids: tuple = hashids.decode(self.kwargs['sid'])
        if not ids:
            raise Http404
        qs = (CourseClassAttachment.objects
              .filter(pk=ids[0])
              .select_related('course_class__course'))
        return get_object_or_404(qs)

    def get_permission_object(self):
        return self.protected_object.course_class


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
