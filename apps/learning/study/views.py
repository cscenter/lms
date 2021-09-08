from typing import Iterable

from isoweek import Week
from vanilla import TemplateView

from django.apps import apps
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.utils.translation import gettext_lazy as _
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.urls import reverse
from courses.calendar import CalendarEvent, TimetableEvent
from courses.models import Course, CourseTeacher, Semester
from courses.utils import MonthPeriod, extended_month_date_range, get_current_term_pair
from courses.views import MonthEventsCalendarView, WeekEventsView
from info_blocks.constants import CurrentInfoBlockTags
from info_blocks.models import InfoBlock
from info_blocks.permissions import ViewInternships
from learning import utils
from learning.calendar import get_all_calendar_events, get_student_calendar_events
from learning.forms import AssignmentCommentForm
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment, StudentAssignment
)
from learning.permissions import (
    CreateAssignmentCommentAsLearner, CreateOwnAssignmentSolution,
    EnrollPermissionObject, ViewCourses, ViewOwnStudentAssignment,
    ViewOwnStudentAssignments
)
from learning.services import get_student_classes
from learning.study.services import get_draft_solution, get_solution_form
from learning.views import AssignmentSubmissionBaseView
from learning.views.views import (
    AssignmentCommentUpsertView, AssignmentSubmissionUpsertView
)
from users.constants import Roles
from users.services import get_student_profile


class CalendarFullView(PermissionRequiredMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes in the city of
    the authenticated student.
    """
    permission_required = "study.view_schedule"

    def get_events(self, month_period: MonthPeriod, **kwargs) -> Iterable:
        start_date, end_date = extended_month_date_range(month_period, expand=1)
        user = self.request.user
        student_profile = get_student_profile(user, self.request.site)
        branches = [student_profile.branch_id]
        return get_all_calendar_events(branch_list=branches, start_date=start_date,
                                       end_date=end_date, time_zone=user.time_zone)


class CalendarPersonalView(CalendarFullView):
    """
    Shows non-course events filtered by student city and classes for courses
    on which authenticated student enrolled.
    """
    calendar_type = "student"
    template_name = "lms/courses/calendar.html"

    def get_events(self, month_period: MonthPeriod, **kwargs) -> Iterable:
        start_date, end_date = extended_month_date_range(month_period, expand=1)
        student_profile = get_student_profile(self.request.user,
                                              self.request.site)
        if not student_profile:
            return []
        return get_student_calendar_events(student_profile=student_profile,
                                           start_date=start_date,
                                           end_date=end_date)


class TimetableView(PermissionRequiredMixin, WeekEventsView):
    """Shows classes for courses which authorized student enrolled in"""
    template_name = "lms/learning/timetable.html"
    permission_required = "study.view_schedule"

    def get_events(self, iso_year, iso_week) -> Iterable[CalendarEvent]:
        w = Week(iso_year, iso_week)
        in_range = [Q(date__range=[w.monday(), w.sunday()])]
        user = self.request.user
        for c in get_student_classes(user, in_range, with_venue=True):
            yield TimetableEvent.create(c, time_zone=user.time_zone)


class StudentAssignmentListView(PermissionRequiredMixin, TemplateView):
    """Shows assignments for the current term."""
    template_name = "lms/study/assignment_list.html"
    permission_required = ViewOwnStudentAssignments.name

    def get_queryset(self, current_term):
        return (StudentAssignment.objects
                .for_student(self.request.user)
                .in_term(current_term)
                .order_by('assignment__deadline_at',
                          'assignment__course__meta_course__name',
                          'pk'))

    def get_context_data(self, **kwargs):
        current_term = Semester.get_current()
        student = self.request.user
        assignment_list = self.get_queryset(current_term)
        enrolled_in = (Enrollment.active
                       .filter(course__semester=current_term, student=student)
                       .values_list("course", flat=True))
        in_progress, archive = utils.split_on_condition(
            assignment_list,
            lambda sa: not sa.assignment.deadline_is_exceeded and
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
            'tz_override': student.time_zone,
            'reporting_periods': reporting_periods
        }
        return context


class StudentAssignmentDetailView(PermissionRequiredMixin,
                                  AssignmentSubmissionBaseView):
    template_name = "learning/study/student_assignment_detail.html"
    permission_required = ViewOwnStudentAssignment.name

    def get_permission_object(self):
        return self.student_assignment

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated:
            course = self.student_assignment.assignment.course
            is_curator = Roles.CURATOR in user.roles
            is_teacher = Roles.TEACHER in user.roles
            if is_curator or (is_teacher and user in course.teachers.all()):
                # Redirects course teacher to the teaching/ section
                raise Redirect(to=self.student_assignment.get_teacher_url())
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sa = self.student_assignment
        comment_form = context['comment_form']
        add_comment_url = reverse('study:assignment_comment_create',
                                  kwargs={'pk': sa.pk})
        comment_form.helper.form_action = add_comment_url
        # Format datetime in student timezone
        context['timezone'] = self.request.user.time_zone
        # Solution Form
        draft_solution = get_draft_solution(self.request.user, sa)
        solution_form = get_solution_form(sa, instance=draft_solution)
        if solution_form:
            add_solution_url = reverse('study:assignment_solution_create',
                                       kwargs={'pk': sa.pk})
            solution_form.helper.form_action = add_solution_url
        context['solution_form'] = solution_form
        return context


class StudentAssignmentCommentCreateView(PermissionRequiredMixin,
                                         AssignmentCommentUpsertView):
    permission_required = CreateAssignmentCommentAsLearner.name
    submission_type = AssignmentSubmissionTypes.COMMENT

    def get_permission_object(self):
        return self.student_assignment

    def get_form_class(self):
        return AssignmentCommentForm

    def get_success_url(self):
        msg = _("Comment successfully saved")
        messages.success(self.request, msg)
        return self.student_assignment.get_student_url()

    def get_error_url(self):
        return self.student_assignment.get_student_url()


class StudentAssignmentSolutionCreateView(PermissionRequiredMixin,
                                          AssignmentSubmissionUpsertView):
    permission_required = CreateOwnAssignmentSolution.name
    submission_type = AssignmentSubmissionTypes.SOLUTION

    def get_permission_object(self):
        return self.student_assignment

    def get_form(self, data=None, files=None, **kwargs):
        solution_form = get_solution_form(self.student_assignment, data=data,
                                          files=files, **kwargs)
        return solution_form

    def get_success_url(self):
        msg = _("Solution successfully saved")
        messages.success(self.request, msg)
        return self.student_assignment.get_student_url()

    def post(self, request, *args, **kwargs):
        submission = AssignmentComment(
            student_assignment=self.student_assignment,
            author=request.user,
            type=self.submission_type,
            is_published=True)
        form = self.get_form(data=request.POST, files=request.FILES,
                             instance=submission)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_error_url(self):
        return self.student_assignment.get_student_url()


class CourseListView(PermissionRequiredMixin, generic.TemplateView):
    model = Course
    context_object_name = 'course_list'
    template_name = "lms/study/course_list.html"
    permission_required = ViewCourses.name

    def get_context_data(self, **kwargs):
        auth_user = self.request.user
        student_enrollments = (Enrollment.active
                               .filter(student_id=auth_user)
                               .select_related("course")
                               .only('id', 'grade', 'course_id', 'course__grading_type'))
        student_enrollments = {e.course_id: e for e in student_enrollments}
        # Get current term course offerings available in student branch
        # and all courses that student enrolled in
        student_profile = get_student_profile(auth_user, self.request.site)
        current_term = get_current_term_pair(auth_user.time_zone)
        current_term_index = current_term.index
        in_student_branch = Q(coursebranch__branch=student_profile.branch_id)
        in_current_term = Q(semester__index=current_term_index)
        enrolled_in = Q(id__in=list(student_enrollments))
        prefetch_teachers = Prefetch('course_teachers',
                                     queryset=CourseTeacher.get_queryset())
        courses = (Course.objects
                   .filter((in_student_branch & in_current_term) | enrolled_in)
                   .select_related('meta_course', 'semester', 'main_branch')
                   .distinct()
                   .order_by('-semester__index', 'meta_course__name', 'pk')
                   .prefetch_related(prefetch_teachers,
                                     "branches",  # it needs for checking permissions
                                     "semester__enrollmentperiod_set"))
        # Group collected courses
        ongoing_enrolled, ongoing_rest, archive = [], [], []
        for course in courses:
            if course.semester.index == current_term_index:
                if course.pk in student_enrollments:
                    ongoing_enrolled.append(course)
                else:
                    ongoing_rest.append(course)
            else:
                archive.append(course)
        context = {
            "enrollments": student_enrollments,
            "ongoing_rest": ongoing_rest,
            "ongoing_enrolled": ongoing_enrolled,
            "archive": archive,
            "current_term": current_term.label.capitalize(),
            "EnrollPermissionObject": EnrollPermissionObject
        }
        return context


class UsefulListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/useful.html"
    permission_required = "study.view_faq"

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(self.request.site)
                .with_tag(CurrentInfoBlockTags.USEFUL)
                .order_by("sort"))


class InternshipListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/internships.html"
    permission_required = ViewInternships.name

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(self.request.site)
                .with_tag(CurrentInfoBlockTags.INTERNSHIP)
                .order_by("sort"))


class HonorCodeView(generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/honor_code.html"

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(self.request.site)
                .with_tag(CurrentInfoBlockTags.HONOR_CODE)
                .order_by("sort"))
