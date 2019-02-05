from typing import Iterable

from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from isoweek import Week
from vanilla import CreateView, ListView

from core.exceptions import Redirect
from core.utils import is_club_site
from courses.calendar import CalendarEvent
from courses.models import CourseClass, Semester, Course
from courses.settings import SemesterTypes
from courses.utils import get_current_term_pair, get_term_index
from courses.views import WeekEventsView, MonthEventsCalendarView
from learning import utils
from learning.calendar import get_month_events
from learning.enrollment import course_failed_by_student
from learning.internships.models import Internship
from learning.models import Useful, StudentAssignment, Enrollment
from learning.permissions import course_access_role, CourseRole
from learning.views import AssignmentSubmissionBaseView
from users.mixins import StudentOnlyMixin
from users.utils import get_student_city_code


class CalendarFullView(StudentOnlyMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes in the city of
    the authenticated student.
    """
    def get_default_timezone(self):
        return get_student_city_code(self.request)

    def get_events(self, year, month, **kwargs):
        student_city_code = self.get_default_timezone()
        return get_month_events(year, month, [student_city_code])


class CalendarPersonalView(CalendarFullView):
    """
    Shows non-course events filtered by student city and classes for courses
    on which authenticated student enrolled.
    """
    calendar_type = "student"
    template_name = "learning/calendar.html"

    def get_events(self, year, month, **kwargs):
        student_city_code = self.get_default_timezone()
        return get_month_events(year, month, [student_city_code],
                                for_student=self.request.user)


class StudentAssignmentListView(StudentOnlyMixin, ListView):
    """ Show assignments from current semester only. """
    model = StudentAssignment
    context_object_name = 'assignment_list'
    template_name = "learning/study/assignment_list.html"

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


class StudentAssignmentDetailView(AssignmentSubmissionBaseView):
    template_name = "learning/study/student_assignment_detail.html"

    def test_func(self, user):
        # Expelled student can't send new submissions or comments
        if self.request.method == "POST":
            is_student = user.is_active_student
        else:
            is_student = user.is_student
        return (is_student or user.is_curator or user.is_graduate or
                user.is_teacher)

    def has_access(self, user, student_assignment):
        sa = student_assignment
        course = student_assignment.assignment.course
        role = course_access_role(course=course, user=user)
        if role == CourseRole.CURATOR:
            return True
        elif role == CourseRole.TEACHER and user in course.teachers.all():
            # Redirects actual course teacher to the teaching/ section
            raise Redirect(to=sa.get_teacher_url())
        elif sa.student == user:
            if role == CourseRole.STUDENT_RESTRICT:
                # If student failed the course or was expelled at all, deny
                # access only when he has no submissions or positive
                # grade on assignment
                # XXX: Take into account only student comments since only
                # they could be treated as `submission`.
                return sa.has_comments(user) or sa.score
            else:
                return role == CourseRole.STUDENT_REGULAR
        return False

    def get_context_data(self, form, **kwargs):
        sa = self.student_assignment
        user = self.request.user
        context = super().get_context_data(form, **kwargs)
        # Update `text` label if student has no submissions yet
        if sa.assignment.is_online and not sa.has_comments(self.request.user):
            context['form'].fields.get('text').label = _("Add solution")
        # Format datetime for online courses in student timezone
        if sa.assignment.course.is_correspondence:
            context['timezone'] = settings.TIME_ZONES[user.city_id]
        return context

    def get_success_url(self):
        return self.student_assignment.get_student_url()


class TimetableView(StudentOnlyMixin, WeekEventsView):
    """Shows classes for courses which authorized student enrolled in"""
    template_name = "learning/study/timetable.html"

    def get_default_timezone(self):
        return get_student_city_code(self.request)

    def get_events(self, iso_year, iso_week,
                   **kwargs) -> Iterable[CalendarEvent]:
        # TODO: Add NonCourseEvents like in a calendar view?
        return (CalendarEvent(e) for e in self._get_classes(iso_year, iso_week))

    def _get_classes(self, iso_year, iso_week):
        w = Week(iso_year, iso_week)
        qs = (CourseClass.objects
              .for_timetable()
              .filter(date__range=[w.monday(), w.sunday()])
              .for_student(self.request.user))
        return qs


class UsefulListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/useful.html"

    def get_queryset(self):
        return (Useful.objects
                .filter(site=settings.SITE_ID)
                .order_by("sort"))


class InternshipListView(StudentOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/internships.html"

    def get_queryset(self):
        return (Internship.objects
                .order_by("sort"))


class CourseListView(StudentOnlyMixin, generic.TemplateView):
    model = Course
    context_object_name = 'course_list'
    template_name = "learning/study/course_list.html"

    def get_context_data(self, **kwargs):
        city_code = get_student_city_code(self.request)
        # Student enrollments
        student_enrollments = (Enrollment.active
                               .filter(student_id=self.request.user)
                               .select_related("course")
                               .only('id', 'grade', 'course_id',
                                     'course__grading_type'))
        student_enrolled_in = {e.course_id: e for e in student_enrollments}
        # 1. Union courses from current term and which student enrolled in
        current_year, current_term = get_current_term_pair(city_code)
        current_term_index = get_term_index(current_year, current_term)
        in_current_term = Q(semester__index=current_term_index)
        enrolled_in = Q(id__in=list(student_enrolled_in))
        # Hide summer courses on CS Club site until student enrolled in
        if is_club_site():
            in_current_term &= ~Q(semester__type=SemesterTypes.SUMMER)
        course_offerings = (Course.objects
                            .get_offerings_base_queryset()
                            .in_city(city_code)
                            .filter(in_current_term | enrolled_in))
        # 2. And split them by type.
        ongoing_enrolled, ongoing_rest, archive_enrolled = [], [], []
        for course in course_offerings:
            if course.semester.index == current_term_index:
                if course.pk in student_enrolled_in:
                    # TODO: add `enrollments` to context and get grades explicitly in tmpl
                    course.enrollment = student_enrolled_in[course.pk]
                    ongoing_enrolled.append(course)
                else:
                    ongoing_rest.append(course)
            else:
                course.enrollment = student_enrolled_in[course.pk]
                archive_enrolled.append(course)
        context = {
            "ongoing_rest": ongoing_rest,
            "ongoing_enrolled": ongoing_enrolled,
            "archive_enrolled": archive_enrolled,
            # FIXME: what about custom template tag for this?
            # TODO: Add util method
            "current_term": "{} {}".format(SemesterTypes.values[current_term],
                                           current_year).capitalize()
        }
        return context
