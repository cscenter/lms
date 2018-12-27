from django.core.exceptions import PermissionDenied
from django.db.models import F, Value, TextField
from django.db.models.functions import Concat
from django.http import HttpResponseForbidden, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views import generic
from vanilla import FormView

from core.constants import DATE_FORMAT_RU
from courses.models import Course
from learning.enrollment.forms import CourseEnrollmentForm
from learning.models import Enrollment
from learning.viewmixins import StudentOnlyMixin


class CourseEnrollView(StudentOnlyMixin, FormView):
    form_class = CourseEnrollmentForm
    template_name = "learning/courses/enrollment.html"

    def get(self, request, *args, **kwargs):
        form = self.get_form(**kwargs)
        if not form.is_available():
            # FIXME: старое поведение - это 404. Может сохранить? Для законченных курсов вроде 404 - ок
            return HttpResponseForbidden()
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST, files=request.FILES, **kwargs)
        if not form.is_available():
            return HttpResponseForbidden()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_form(self, data=None, files=None, **kwargs):
        course_slug = kwargs["course_slug"]
        try:
            semester_year, semester_type = kwargs["semester_slug"].split("-", 1)
        except ValueError:
            raise Http404
        course = get_object_or_404(
            Course.objects
            .filter(meta_course__slug=course_slug,
                    semester__year=semester_year,
                    semester__type=semester_type)
            .in_city(self.request.city_code)
            .select_related("semester")
        )
        return CourseEnrollmentForm(data=data, files=files,
                                    request=self.request, course=course)

    def form_valid(self, form):
        enrollment, _ = Enrollment.objects.update_or_create(
            student=form.request.user,
            course=form.course,
            defaults={'is_deleted': False})
        reason = form.cleaned_data["reason"].strip()
        if reason:
            if enrollment.reason_entry:
                today = enrollment.modified.strftime(DATE_FORMAT_RU)
                reason = Concat(F('reason_entry'),
                                Value(f'\n------\n{today}\n{reason}'),
                                output_field=TextField())
            (Enrollment.objects
             .filter(pk=enrollment.pk)
             .update(reason_entry=reason))
        if self.request.POST.get('back') == 'course_list_student':
            return redirect('course_list_student')
        else:
            return HttpResponseRedirect(form.course.get_absolute_url())


class CourseUnenrollView(StudentOnlyMixin, generic.DeleteView):
    template_name = "learning/courses/enrollment_leave.html"
    context_object_name = "enrollment"

    def __init__(self, *args, **kwargs):
        self._course = None
        super().__init__(*args, **kwargs)

    def get_object(self, _=None):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        enrollment = get_object_or_404(
            Enrollment.active
            .filter(
                student=self.request.user,
                course__city_id=self.request.city_code,
                course__semester__type=semester_type,
                course__semester__year=year,
                course__meta_course__slug=self.kwargs['course_slug'])
            .select_related("course", "course__semester"))
        self._course = enrollment.course
        if not self._course.enrollment_is_open:
            raise PermissionDenied
        return enrollment

    def delete(self, request, *args, **kwargs):
        enrollment = self.get_object()
        update_fields = {"is_deleted": True}
        reason_leave = request.POST.get("reason", "").strip()
        if reason_leave:
            today = now().strftime(DATE_FORMAT_RU)
            if enrollment.reason_leave:
                update_fields["reason_leave"] = Concat(
                    F('reason_leave'),
                    Value(f'\n------\n{today}\n{reason_leave}'),
                    output_field=TextField())
            else:
                update_fields["reason_leave"] = f'{today}\n{reason_leave}'
        Enrollment.active.filter(pk=enrollment.pk).update(**update_fields)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if self.request.GET.get('back') == 'course_list_student':
            return reverse('course_list_student')
        else:
            return self._course.get_absolute_url()