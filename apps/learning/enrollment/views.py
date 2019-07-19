from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Value, TextField, Q, OuterRef
from django.db.models.functions import Concat
from django.db.models.signals import post_save
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.views import generic
from vanilla import FormView
from django.utils.translation import ugettext_lazy as _

from core.constants import DATE_FORMAT_RU
from core.db.expressions import SubqueryCount
from core.exceptions import Redirect
from core.timezone import now_local
from core.urls import reverse
from courses.models import Course
from courses.views.mixins import CourseURLParamsMixin
from learning.enrollment.forms import CourseEnrollmentForm
from learning.models import Enrollment
from learning.utils import populate_assignments_for_student
from users.mixins import StudentOnlyMixin


class CourseEnrollView(StudentOnlyMixin, CourseURLParamsMixin, FormView):
    form_class = CourseEnrollmentForm
    template_name = "learning/enrollment/enrollment_enter.html"

    def get_course_queryset(self):
        return (super().get_course_queryset()
                .select_related("semester"))

    def get(self, request, *args, **kwargs):
        if self.course.is_capacity_limited and not self.course.places_left:
            msg = _("No places available, sorry")
            messages.error(self.request, msg, extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())

        form = self.get_form(**kwargs)

        if not request.user.has_perm("learning.can_enroll_in_course", self.course):
            return HttpResponseForbidden()

        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        # FIXME: Possible race condition on saving form!
        # Reject if capacity limited and no places available
        # XXX: Race condition. Should be placed in save method
        if self.course.is_capacity_limited:
            if not self.course.places_left:
                msg = _("No places available, sorry")
                messages.error(self.request, msg, extra_tags='timeout')
                raise Redirect(to=self.course.get_absolute_url())
        form = self.get_form(data=request.POST, files=request.FILES)
        if not request.user.has_perm("learning.can_enroll_in_course", self.course):
            return HttpResponseForbidden()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        reason = form.cleaned_data["reason"].strip()
        if reason:
            timezone = self.course.get_city_timezone()
            today = now_local(timezone).strftime(DATE_FORMAT_RU)
            reason = Concat(Value(f'{today}\n{reason}\n\n'),
                            F('reason_entry'),
                            output_field=TextField())
        enrollment, created = (Enrollment.objects.get_or_create(
            student=self.request.user,
            course=self.course,
            defaults={'is_deleted': True}))
        if not enrollment.is_deleted:
            # FIXME: wtf. Show message "You are already enrolled in the course"
            pass
        # Try to update state of the enrollment record to `active`
        filters = [Q(pk=enrollment.pk), Q(is_deleted=True)]
        if self.course.is_capacity_limited:
            # FIXME: т.к. дефолтный уровень изоляции read commited, то должен быть лок на операции update,
            # 2я транзация будет ждать, пока первая выполнит commit() или rollback(). А значит
            # если апдейт кэша для learners_count поместить в транзацию, то там уже будет актуальное значение и можно убрать подзапрос. подумать на свежую башку
            learners_count = SubqueryCount(
                Enrollment.active
                .filter(course_id=OuterRef('course_id')))
            filters.append(Q(course__capacity__gt=learners_count))
        updated = (Enrollment.objects
                   .filter(*filters)
                   .update(is_deleted=False, reason_entry=reason))
        if not updated:
            # At this point we don't know the exact reason why row wasn't
            # updated. It could happen if the enrollment state was
            # `is_deleted=False` or no places left or both.
            # The first one is really rare (user should do concurrent requests)
            # and still should be considered as success, so let's take into
            # account only the second case.
            if self.course.is_capacity_limited:
                # FIXME: тут неплохо бы откатить новую запись, если была добавлена
                # TODO: rollback if created == True
                pass
        else:
            if not created:
                # FIXME: а может всегда эту логику держать тут? а из модели убрать
                populate_assignments_for_student(enrollment)
            # Recalculate learners count
            enrollment.is_deleted = False
            enrollment.reason_entry = reason
            post_save.send(Enrollment, instance=enrollment, created=False)
        if self.request.POST.get('back') == 'study:course_list':
            return redirect(reverse('study:course_list'))
        else:
            return HttpResponseRedirect(self.course.get_absolute_url())


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
