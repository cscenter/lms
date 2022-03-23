from typing import Iterable, List

from django.shortcuts import redirect
from isoweek import Week
from vanilla import GenericModelView, TemplateView

from django.apps import apps
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core import comment_persistence
from core.exceptions import Redirect
from core.http import HttpRequest
from core.timezone import get_now_utc
from core.urls import reverse
from courses.calendar import CalendarEvent, TimetableEvent
from courses.models import Course, Semester
from courses.selectors import course_teachers_prefetch_queryset
from courses.utils import MonthPeriod, extended_month_date_range, get_current_term_pair
from courses.views import MonthEventsCalendarView, WeekEventsView
from info_blocks.constants import CurrentInfoBlockTags
from info_blocks.models import InfoBlock
from info_blocks.permissions import ViewInternships
from learning import utils
from learning.calendar import get_all_calendar_events, get_student_calendar_events
from learning.models import Enrollment, StudentAssignment
from learning.permissions import (
    CreateAssignmentCommentAsLearner, CreateOwnAssignmentSolution,
    EnrollPermissionObject, ViewCourses, ViewOwnStudentAssignment,
    ViewOwnStudentAssignments
)
from learning.selectors import get_student_classes
from learning.services.personal_assignment_service import (
    get_assignment_update_history_message, get_draft_comment
)
from learning.study.forms import AssignmentCommentForm, StudentAssignmentListFilter
from learning.study.services import get_solution_form, save_solution_form, get_current_semester_active_courses
from learning.views import AssignmentSubmissionBaseView
from learning.views.views import (
    AssignmentCommentUpsertView, StudentAssignmentURLParamsMixin
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
        today = get_now_utc().date()
        return (StudentAssignment.objects
                .for_student(self.request.user)
                .filter(assignment__course__completed_at__gt=today)
                .order_by('assignment__deadline_at',
                          'assignment__course__meta_course__name',
                          'pk'))

    def get_context_data(self, filter_form: StudentAssignmentListFilter,
                         enrolled_in_courses: List[int],
                         current_term: Semester, **kwargs):
        student = self.request.user
        assignment_list = self.get_queryset(current_term)
        filter_course = kwargs.get("course", None)
        if filter_course is not None:
            assignment_list = filter(
                lambda sa: sa.assignment.course_id == filter_course,
                assignment_list
            )
        in_progress, archive = utils.split_on_condition(
            assignment_list,
            lambda sa: not sa.assignment.deadline_is_exceeded and
                       sa.assignment.course_id in enrolled_in_courses)
        archive.reverse()
        # Map student projects in current term to related reporting periods
        reporting_periods = None
        if apps.is_installed("projects"):
            from projects.services import get_project_reporting_periods
            reporting_periods = get_project_reporting_periods(student,
                                                              current_term)
        context = {
            'course_filter_form': filter_form,
            'assignment_list_open': in_progress,
            'assignment_list_archive': archive,
            'tz_override': student.time_zone,
            'reporting_periods': reporting_periods
        }
        return context

    def get(self, request, *args, **kwargs):
        current_term = Semester.get_current()
        enrolled_in = get_current_semester_active_courses(request.user, current_term)
        filter_form = StudentAssignmentListFilter(enrolled_in, data=request.GET)
        filter_course = None
        if filter_form.is_valid():
            filter_course = filter_form.cleaned_data["course"]
        context = self.get_context_data(filter_form=filter_form,
                                        enrolled_in_courses=enrolled_in,
                                        current_term=current_term,
                                        course=filter_course, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        current_term = Semester.get_current()
        enrolled_in = get_current_semester_active_courses(request.user, Semester.get_current())
        filter_form = StudentAssignmentListFilter(enrolled_in,
                                                  data=request.POST)
        filter_course = None
        if filter_form.is_valid():
            filter_course = filter_form.cleaned_data["course"]
            url = reverse('study:assignment_list')
            if filter_course is not None:
                url = f"{url}?course={filter_course}"
            return redirect(url)
        context = self.get_context_data(filter_form=filter_form,
                                        enrolled_in_courses=enrolled_in,
                                        current_term=current_term,
                                        course=filter_course, **kwargs)
        return self.render_to_response(context)


class StudentAssignmentDetailView(PermissionRequiredMixin,
                                  AssignmentSubmissionBaseView):
    template_name = "lms/study/student_assignment_detail.html"
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
        draft_comment = get_draft_comment(self.request.user, self.student_assignment)
        comment_form = AssignmentCommentForm(instance=draft_comment)
        add_comment_url = reverse('study:assignment_comment_create',
                                  kwargs={'pk': sa.pk})
        comment_form.helper.form_action = add_comment_url
        # Format datetime in student timezone
        context['comment_form'] = comment_form
        context['time_zone'] = self.request.user.time_zone
        context['solution_form'] = get_solution_form(sa)
        context['get_score_status_changing_message'] = get_assignment_update_history_message
        return context


class StudentAssignmentCommentCreateView(PermissionRequiredMixin,
                                         AssignmentCommentUpsertView):
    permission_required = CreateAssignmentCommentAsLearner.name

    def get_permission_object(self):
        return self.student_assignment

    def get_success_url(self):
        msg = _("Comment successfully saved")
        messages.success(self.request, msg)
        return self.student_assignment.get_student_url()

    def get_error_url(self):
        return self.student_assignment.get_student_url()


class StudentAssignmentSolutionCreateView(PermissionRequiredMixin,
                                          StudentAssignmentURLParamsMixin,
                                          GenericModelView):
    permission_required = CreateOwnAssignmentSolution.name

    def get_permission_object(self):
        return self.student_assignment

    def form_invalid(self, form):
        msg = "<br>".join("<br>".join(errors)
                          for errors in form.errors.values())
        messages.error(self.request, "Данные не сохранены!<br>" + msg)
        redirect_to = self.student_assignment.get_student_url()
        return HttpResponseRedirect(redirect_to)

    def post(self, request, *args, **kwargs):
        solution_form = get_solution_form(self.student_assignment, data=request.POST,
                                          files=request.FILES)
        if solution_form is None:
            return HttpResponseBadRequest("Assignment format doesn't support this method")
        if solution_form.is_valid():
            with transaction.atomic():
                submission = save_solution_form(form=solution_form,
                                                personal_assignment=self.student_assignment,
                                                created_by=request.user)
            if submission.text:
                comment_persistence.add_to_gc(submission.text)
            msg = _("Solution successfully saved")
            messages.success(self.request, msg)
            redirect_to = self.student_assignment.get_student_url()
            return HttpResponseRedirect(redirect_to)
        return self.form_invalid(solution_form)


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
                                     queryset=course_teachers_prefetch_queryset())
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
    request: HttpRequest

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
