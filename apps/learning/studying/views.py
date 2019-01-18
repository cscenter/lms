import datetime
from itertools import chain
from typing import Iterable

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import CreateView, ListView

from core.exceptions import Redirect
from courses.calendar import CalendarEvent
from courses.models import CourseClass, Semester
from courses.views import WeekEventsView, MonthEventsCalendarView
from learning import utils
from learning.enrollment import course_failed_by_student
from learning.internships.models import Internship
from learning.models import Useful, StudentAssignment, Enrollment, \
    NonCourseEvent
from learning.utils import iso_to_gregorian
from learning.views import AssignmentProgressBaseView
from learning.views.utils import get_student_city_code
from users.mixins import StudentOnlyMixin


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
        if user.city_code and (user.is_student or user.is_volunteer):
            tz_override = settings.TIME_ZONES[user.city_code]
        context["tz_override"] = tz_override
        return context


class StudentAssignmentStudentDetailView(AssignmentProgressBaseView,
                                         CreateView):
    user_type = 'student'
    template_name = "learning/assignment_submission_detail.html"

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


class TimetableView(StudentOnlyMixin, WeekEventsView):
    """Shows classes for courses which authorized student enrolled in"""
    template_name = "learning/studying/timetable.html"

    def get_default_timezone(self):
        return get_student_city_code(self.request)

    def get_events(self, iso_year, iso_week,
                   **kwargs) -> Iterable[CalendarEvent]:
        # TODO: Add NonCourseEvents like in a calendar view?
        return (CalendarEvent(e) for e in self._get_classes(iso_year, iso_week))

    def _get_classes(self, iso_year, iso_week):
        week_start = iso_to_gregorian(iso_year, iso_week, iso_week_day=1)
        week_end = week_start + datetime.timedelta(days=6)
        qs = (CourseClass.objects
              .filter(date__range=[week_start, week_end])
              .for_student(self.request.user)
              .for_timetable(self.request.user))
        return qs


class CalendarStudentFullView(StudentOnlyMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes in the city of
    the authenticated student.
    """
    def get_default_timezone(self):
        return get_student_city_code(self.request)

    def get_events(self, year, month, **kwargs):
        student_city_code = self.get_default_timezone()
        return chain(
            (CalendarEvent(e) for e in
                self._get_classes(year, month, student_city_code)),
            (CalendarEvent(e) for e in
                self._get_non_course_events(year, month, student_city_code))
        )

    @staticmethod
    def _get_non_course_events(year, month, city_code):
        return (NonCourseEvent.objects
                .for_calendar()
                .for_city(city_code)
                .in_month(year, month))

    def _get_classes(self, year, month, city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .in_city(city_code))


class CalendarStudentPersonalView(CalendarStudentFullView):
    """
    Shows non-course events filtered by student city and classes for courses
    on which authenticated student enrolled.
    """
    calendar_type = "student"
    template_name = "learning/calendar.html"

    def _get_classes(self, year, month, city_code):
        qs = super()._get_classes(year, month, city_code)
        return qs.for_student(self.request.user)


class UsefulListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/studying/useful.html"

    def get_queryset(self):
        return (Useful.objects
                .filter(site=settings.SITE_ID)
                .order_by("sort"))


class InternshipListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/studying/internships.html"

    def get_queryset(self):
        return (Internship.objects
                .order_by("sort"))

