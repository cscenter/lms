from django.core.exceptions import PermissionDenied
from django.db.models import F, Value, TextField
from django.db.models.functions import Concat
from django.http import HttpResponseForbidden, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.views import generic
from vanilla import FormView

from core.constants import DATE_FORMAT_RU
from core.urls import reverse
from courses.models import Course
from courses.views.mixins import CourseURLParamsMixin
from learning.enrollment.forms import CourseEnrollmentForm
from learning.models import Enrollment
from users.mixins import StudentOnlyMixin


class CourseEnrollView(StudentOnlyMixin, CourseURLParamsMixin, FormView):
    form_class = CourseEnrollmentForm
    template_name = "learning/courses/enrollment.html"

    def get(self, request, *args, **kwargs):
        form = self.get_form(**kwargs)
        if not form.is_available():
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
        course = get_object_or_404(self.get_course_queryset()
                                   .select_related("semester"))
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
        if self.request.POST.get('back') == 'study:course_list':
            return redirect(reverse('study:course_list'))
        else:
            return HttpResponseRedirect(form.course.get_absolute_url())


class CourseUnenrollView(StudentOnlyMixin, CourseURLParamsMixin,
                         generic.DeleteView):
    template_name = "learning/courses/enrollment_leave.html"
    context_object_name = "enrollment"

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
        if self.request.GET.get('back') == 'study:course_list':
            success_url = reverse('study:course_list')
        else:
            success_url = enrollment.course.get_absolute_url()
        return HttpResponseRedirect(success_url)

    def get_object(self, queryset=None):
        course = get_object_or_404(self.get_course_queryset())
        enrollment = get_object_or_404(
            Enrollment.active
                .filter(student=self.request.user, course_id=course.pk)
                .select_related("course", "course__semester"))
        if not course.enrollment_is_open:
            raise PermissionDenied
        return enrollment
