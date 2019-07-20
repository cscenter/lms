from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Value, TextField
from django.db.models.functions import Concat
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import FormView

from core.constants import DATE_FORMAT_RU
from core.exceptions import Redirect
from core.urls import reverse
from courses.views.mixins import CourseURLParamsMixin
from learning.forms import CourseEnrollmentForm
from learning.models import Enrollment
from learning.services import EnrollmentService, AlreadyEnrolled, \
    CourseCapacityFull
from users.mixins import StudentOnlyMixin


class CourseEnrollView(StudentOnlyMixin, CourseURLParamsMixin, FormView):
    form_class = CourseEnrollmentForm
    template_name = "learning/enrollment/enrollment_enter.html"

    def get_course_queryset(self):
        return (super().get_course_queryset()
                .select_related("semester", "meta_course"))

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm("learning.can_enroll_in_course",
                                     self.course):
            # Student was unlucky enough or just slow, let them know
            if self.course.is_capacity_limited and not self.course.places_left:
                msg = _("No places available, sorry")
                messages.error(self.request, msg, extra_tags='timeout')
                raise Redirect(to=self.course.get_absolute_url())
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        reason = form.cleaned_data["reason"].strip()
        try:
            EnrollmentService.enroll(self.request.user, self.course, reason)
        except AlreadyEnrolled:
            msg = _("You are already enrolled in the course")
            messages.warning(self.request, msg, extra_tags='timeout')
        except CourseCapacityFull:
            msg = _("No places available, sorry")
            messages.error(self.request, msg, extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())
        if self.request.POST.get('back') == 'study:course_list':
            return_to = reverse('study:course_list')
        else:
            return_to = self.course.get_absolute_url()
        return HttpResponseRedirect(return_to)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context


class CourseUnenrollView(StudentOnlyMixin, CourseURLParamsMixin,
                         generic.DeleteView):
    template_name = "learning/enrollment/enrollment_leave.html"
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
        for field_name, field_value in update_fields.items():
            setattr(enrollment, field_name, field_value)
        enrollment.save(update_fields=update_fields.keys())
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
