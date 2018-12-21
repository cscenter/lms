from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Value, TextField
from django.db.models.functions import Cast, Concat, Trim
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import CreateView, ListView, TemplateView, FormView

from core.exceptions import Redirect
from core.utils import is_club_site
from learning import utils
from learning.enrollment import course_failed_by_student
from learning.forms import CourseEnrollmentForm
from learning.models import Useful, Internship, StudentAssignment, Enrollment
from courses.models import Course, Semester
from core.constants import DATE_FORMAT_RU
from learning.viewmixins import StudentCenterAndVolunteerOnlyMixin, \
    ParticipantOnlyMixin, StudentOnlyMixin
from learning.views import AssignmentProgressBaseView
from learning.views.utils import get_student_city_code


class UsefulListView(StudentCenterAndVolunteerOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "useful.html"

    def get_queryset(self):
        return (Useful.objects
                .filter(site=settings.CENTER_SITE_ID)
                .order_by("sort"))


class InternshipListView(StudentCenterAndVolunteerOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/internships.html"

    def get_queryset(self):
        return (Internship.objects
                .order_by("sort"))


class StudentAssignmentStudentDetailView(AssignmentProgressBaseView,
                                         CreateView):
    user_type = 'student'

    def has_permissions_coarse(self, user):
        # Expelled students can't send new submissions or comments
        if self.request.method == "POST":
            is_student = user.is_active_student
        else:
            is_student = user.is_student
        return (is_student or user.is_curator or user.is_graduate or
                user.is_teacher)

    def has_permissions_precise(self, user):
        sa = self.student_assignment
        # Redirect actual course teacher to teaching/ section
        if user in sa.assignment.course.teachers.all():
            raise Redirect(to=sa.get_teacher_url())
        # If student failed course, deny access when he has no submissions
        # or positive grade
        if sa.student == user:
            co = sa.assignment.course
            if course_failed_by_student(co, self.request.user):
                if not sa.has_comments(user) and not sa.score:
                    return False
        return sa.student == user or user.is_curator

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        # Update `text` label if student has no submissions yet
        sa = self.student_assignment
        if sa.assignment.is_online and not sa.has_comments(self.request.user):
            context['form'].fields.get('text').label = _("Add solution")
        return context

    def get_success_url(self):
        return self.student_assignment.get_student_url()


class StudentAssignmentListView(StudentOnlyMixin, ListView):
    """ Show assignments from current semester only. """
    model = StudentAssignment
    context_object_name = 'assignment_list'
    template_name = "learning/assignment_list_student.html"

    def get_queryset(self):
        current_semester = Semester.get_current()
        self.current_semester = current_semester
        return (StudentAssignment.objects
                .filter(student=self.request.user,
                        assignment__course__semester=current_semester)
                .order_by('assignment__deadline_at',
                          'assignment__course__meta_course__name',
                          'pk')
                # FIXME: this prefetch doesn't seem to work properly
                .prefetch_related('assignmentnotification_set')
                .select_related('assignment',
                                'assignment__course',
                                'assignment__course__meta_course',
                                'assignment__course__semester',
                                'student'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrolled_in = (Enrollment.active
                       .filter(course__semester=self.current_semester,
                               student=self.request.user)
                       .values_list("course", flat=True))
        open_, archive = utils.split_on_condition(
            context['assignment_list'],
            lambda sa: sa.assignment.is_open and
                       sa.assignment.course_id in enrolled_in)
        archive.reverse()
        context['assignment_list_open'] = open_
        context['assignment_list_archive'] = archive
        user = self.request.user
        # Since this view for students only, check only city settings
        tz_override = None
        if user.city_code and (user.is_student_center or user.is_volunteer):
            tz_override = settings.TIME_ZONES[user.city_code]
        context["tz_override"] = tz_override
        return context


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
