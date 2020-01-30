from typing import Iterable

from django.apps import apps
from django.conf import settings
from django.db.models import Q, Prefetch
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from isoweek import Week
from vanilla import ListView, TemplateView

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.urls import reverse
from core.utils import is_club_site
from courses.calendar import CalendarEvent
from courses.constants import SemesterTypes
from courses.models import CourseClass, Semester, Course
from courses.utils import get_current_term_pair, get_term_index
from courses.views import WeekEventsView, MonthEventsCalendarView
from learning import utils
from learning.calendar import get_student_month_events
from learning.internships.models import Internship
from learning.models import Useful, StudentAssignment, Enrollment
from learning.permissions import ViewOwnAssignments
from learning.roles import Roles
from learning.views import AssignmentSubmissionBaseView
from learning.views.views import AssignmentCommentUpsertView
from users.models import User


class CalendarFullView(PermissionRequiredMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes in the city of
    the authenticated student.
    """
    permission_required = "study.view_schedule"

    def get_events(self, year, month, **kwargs):
        return get_student_month_events(self.request.user, year, month)


class CalendarPersonalView(CalendarFullView):
    """
    Shows non-course events filtered by student city and classes for courses
    on which authenticated student enrolled.
    """
    calendar_type = "student"
    template_name = "learning/calendar.html"

    def get_events(self, year, month, **kwargs):
        return get_student_month_events(self.request.user, year, month,
                                        personal=True)


class TimetableView(PermissionRequiredMixin, WeekEventsView):
    """Shows classes for courses which authorized student enrolled in"""
    template_name = "learning/study/timetable.html"
    permission_required = "study.view_schedule"

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


class StudentAssignmentListView(PermissionRequiredMixin, TemplateView):
    """Shows assignments for the current term."""
    template_name = "learning/study/assignment_list.html"
    permission_required = ViewOwnAssignments.name

    def get_queryset(self, current_term):
        return (StudentAssignment.objects
                .filter(student=self.request.user,
                        assignment__course__semester=current_term)
                .order_by('assignment__deadline_at',
                          'assignment__course__meta_course__name',
                          'pk')
                .select_related('assignment',
                                'assignment__course',
                                'assignment__course__meta_course',
                                'assignment__course__semester',
                                'assignment__course__branch',
                                'student'))

    def get_context_data(self, **kwargs):
        current_term = Semester.get_current()
        student = self.request.user
        assignment_list = self.get_queryset(current_term)
        enrolled_in = (Enrollment.active
                       .filter(course__semester=current_term, student=student)
                       .values_list("course", flat=True))
        in_progress, archive = utils.split_on_condition(
            assignment_list,
            lambda sa: sa.assignment.is_open and
                       sa.assignment.course_id in enrolled_in)
        archive.reverse()
        # Map student projects in current term to related reporting periods
        reporting_periods = None
        if apps.is_installed("projects"):
            from projects.services import get_project_reporting_periods
            reporting_periods = get_project_reporting_periods(student,
                                                              current_term)
        context = {
            'assignment_list_open': in_progress,
            'assignment_list_archive': archive,
            'tz_override': student.get_timezone(),
            'reporting_periods': reporting_periods
        }
        return context


class StudentAssignmentDetailView(PermissionRequiredMixin,
                                  AssignmentSubmissionBaseView):
    template_name = "learning/study/student_assignment_detail.html"

    def has_permission(self):
        user = self.request.user
        if user.has_perm("study.view_own_assignment", self.student_assignment):
            return True
        course = self.student_assignment.assignment.course
        if Roles.TEACHER in user.roles and user in course.teachers.all():
            # Redirects actual course teacher to the teaching/ section
            raise Redirect(to=self.student_assignment.get_teacher_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sa = self.student_assignment
        comment_form = context['comment_form']
        comment_form.helper.form_action = reverse(
            'study:assignment_comment_create',
            kwargs={'pk': sa.pk})
        # Update `text` label if student has no submissions yet
        if sa.assignment.is_online2 and not sa.has_comments(self.request.user):
            comment_form.fields.get('text').label = _("Add solution")
        # Format datetime in student timezone
        context['timezone'] = self.request.user.get_timezone()
        return context


class StudentAssignmentCommentCreateView(PermissionRequiredMixin,
                                         AssignmentCommentUpsertView):
    permission_required = "study.create_assignment_comment"

    def get_permission_object(self):
        return self.student_assignment

    def get_success_url(self):
        return self.student_assignment.get_student_url()


class UsefulListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/useful.html"
    permission_required = "study.view_faq"

    def get_queryset(self):
        return (Useful.objects
                .filter(site=settings.SITE_ID)
                .order_by("sort"))


class InternshipListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/internships.html"
    permission_required = "study.view_internships"

    def get_queryset(self):
        return (Internship.objects
                .order_by("sort"))


class CourseListView(PermissionRequiredMixin, generic.TemplateView):
    model = Course
    context_object_name = 'course_list'
    template_name = "learning/study/course_list.html"
    permission_required = "study.view_courses"

    def get_context_data(self, **kwargs):
        # Student enrollments
        student_enrollments = (Enrollment.active
                               .filter(student_id=self.request.user)
                               .select_related("course")
                               .only('id', 'grade', 'course_id',
                                     'course__grading_type'))
        student_enrolled_in = {e.course_id: e for e in student_enrollments}
        # 1. Union courses from current term and which student enrolled in
        tz = self.request.user.get_timezone()
        current_term = get_current_term_pair(tz)
        current_term_index = current_term.index
        in_current_term = Q(semester__index=current_term_index)
        enrolled_in = Q(id__in=list(student_enrolled_in))
        # Hide summer courses on CS Club site until student enrolled in
        if is_club_site():
            in_current_term &= ~Q(semester__type=SemesterTypes.SUMMER)
        prefetch_teachers = Prefetch(
            'teachers',
            queryset=User.objects.only("id", "first_name", "last_name",
                                       "patronymic"))
        course_offerings = (Course.objects
                            .available_in(self.request.user.branch_id)
                            .filter(in_current_term | enrolled_in)
                            .select_related('meta_course', 'semester', 'branch')
                            .prefetch_related(prefetch_teachers,
                                              "additional_branches"))
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
            "current_term": "{} {}".format(
                SemesterTypes.values[current_term.type],
                current_term.year).capitalize()
        }
        return context


class HonorCodeView(generic.TemplateView):
    template_name = "learning/study/honor_code.html"
