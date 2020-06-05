from typing import Iterable

from django.apps import apps
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from isoweek import Week
from vanilla import TemplateView, GenericModelView

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.urls import reverse
from core.utils import is_club_site
from courses.calendar import CalendarEvent
from courses.constants import SemesterTypes
from courses.models import Semester, Course
from courses.utils import get_current_term_pair, MonthPeriod, \
    extended_month_date_range
from courses.views import WeekEventsView, MonthEventsCalendarView
from info_blocks.constants import CurrentInfoBlockTags
from info_blocks.models import InfoBlock
from learning import utils
from learning.calendar import get_student_calendar_events, get_calendar_events
from learning.forms import AssignmentExecutionTimeForm
from learning.models import StudentAssignment, Enrollment
from learning.permissions import ViewOwnStudentAssignments, \
    EditOwnAssignmentExecutionTime, ViewOwnStudentAssignment, ViewCourses
from info_blocks.permissions import ViewInternships
from learning.roles import Roles
from learning.services import get_student_classes
from learning.views import AssignmentSubmissionBaseView
from learning.views.views import AssignmentCommentUpsertView, \
    StudentAssignmentURLParamsMixin
from users.models import User


class CalendarFullView(PermissionRequiredMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes in the city of
    the authenticated student.
    """
    permission_required = "study.view_schedule"

    def get_events(self, month_period: MonthPeriod, **kwargs) -> Iterable:
        branches = [self.request.user.branch_id]
        start_date, end_date = extended_month_date_range(month_period)
        return get_calendar_events(branch_list=branches, start_date=start_date,
                                   end_date=end_date)


class CalendarPersonalView(CalendarFullView):
    """
    Shows non-course events filtered by student city and classes for courses
    on which authenticated student enrolled.
    """
    calendar_type = "student"
    template_name = "learning/calendar.html"

    def get_events(self, month_period: MonthPeriod, **kwargs) -> Iterable:
        start_date, end_date = extended_month_date_range(month_period)
        return get_student_calendar_events(user=self.request.user,
                                           start_date=start_date,
                                           end_date=end_date)


class TimetableView(PermissionRequiredMixin, WeekEventsView):
    """Shows classes for courses which authorized student enrolled in"""
    template_name = "learning/study/timetable.html"
    permission_required = "study.view_schedule"

    def get_events(self, iso_year, iso_week) -> Iterable[CalendarEvent]:
        w = Week(iso_year, iso_week)
        in_range = [Q(date__range=[w.monday(), w.sunday()])]
        cs = get_student_classes(self.request.user, in_range, with_venue=True)
        for c in cs:
            yield CalendarEvent(c)


class StudentAssignmentListView(PermissionRequiredMixin, TemplateView):
    """Shows assignments for the current term."""
    template_name = "learning/study/assignment_list.html"
    permission_required = ViewOwnStudentAssignments.name

    def get_queryset(self, current_term):
        return (StudentAssignment.objects
                .for_user(self.request.user)
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
    permission_required = ViewOwnStudentAssignment.name

    def get_permission_object(self):
        return self.student_assignment

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated:
            course = self.student_assignment.assignment.course
            if Roles.TEACHER in user.roles and user in course.teachers.all():
                # Redirects actual course teacher to the teaching/ section
                raise Redirect(to=self.student_assignment.get_teacher_url())
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sa = self.student_assignment
        comment_form = context['comment_form']
        comment_form.helper.form_action = reverse(
            'study:assignment_comment_create',
            kwargs={'pk': sa.pk})
        # Update `text` label if student has no submissions yet
        if sa.assignment.is_online and not sa.has_comments(self.request.user):
            comment_form.fields.get('text').label = _("Add solution")
        # Format datetime in student timezone
        context['timezone'] = self.request.user.get_timezone()
        execution_time_form = AssignmentExecutionTimeForm(instance=sa)
        context['execution_time_form'] = execution_time_form
        return context


class AssignmentExecutionTimeUpdateView(StudentAssignmentURLParamsMixin,
                                        PermissionRequiredMixin,
                                        GenericModelView):
    permission_required = EditOwnAssignmentExecutionTime.name
    form_class = AssignmentExecutionTimeForm

    def get_permission_object(self):
        return self.student_assignment

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST, files=request.FILES,
                             instance=self.student_assignment)
        if form.is_valid():
            # TODO: update only execution_time field
            self.student_assignment = form.save()
            success_url = self.student_assignment.get_student_url()
            return HttpResponseRedirect(success_url)
        msg = str(_("Form has not been saved."))
        if "execution_time" in form.errors:
            msg = msg + " " + str(_('Wrong time format'))
        messages.error(request, msg)
        return HttpResponseRedirect(self.student_assignment.get_student_url())


class StudentAssignmentCommentCreateView(PermissionRequiredMixin,
                                         AssignmentCommentUpsertView):
    permission_required = "study.create_assignment_comment"

    def get_permission_object(self):
        return self.student_assignment

    def get_success_url(self):
        return self.student_assignment.get_student_url()


class CourseListView(PermissionRequiredMixin, generic.TemplateView):
    model = Course
    context_object_name = 'course_list'
    template_name = "learning/study/course_list.html"
    permission_required = ViewCourses.name

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
                            .select_related('meta_course', 'semester',
                                            'main_branch')
                            .order_by('-semester__index',
                                      'meta_course__name', 'pk')
                            .prefetch_related(prefetch_teachers,
                                              "branches"))
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
