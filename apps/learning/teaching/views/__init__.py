from decimal import Decimal
from typing import Any, Dict, Iterable

from vanilla import TemplateView

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core.db.utils import normalize_score
from core.exceptions import Redirect
from core.http import HttpRequest
from courses.calendar import TimetableEvent
from courses.constants import TeacherRoles
from courses.models import Course, CourseDurations
from courses.selectors import course_teachers_prefetch_queryset
from courses.services import get_teacher_branches, group_teachers
from courses.utils import MonthPeriod, extended_month_date_range, get_current_term_pair
from courses.views.calendar import MonthEventsCalendarView
from courses.views.mixins import CourseURLParamsMixin
from info_blocks.constants import CurrentInfoBlockTags
from info_blocks.models import InfoBlock
from learning.calendar import get_all_calendar_events, get_teacher_calendar_events
from learning.gradebook.views import GradeBookListBaseView
from learning.models import Enrollment, StudentAssignment
from learning.permissions import AccessTeacherSection, CreateCourseNews, ViewEnrollment
from learning.selectors import get_teacher_classes
from learning.teaching.utils import get_student_groups_url
from users.mixins import TeacherOnlyMixin


class TimetableView(TeacherOnlyMixin, MonthEventsCalendarView):
    """
    Shows classes for courses where authorized teacher participate in.
    """
    calendar_type = "teacher"
    template_name = "lms/teaching/timetable.html"

    def get_events(self, month_period: MonthPeriod, **kwargs):
        start, end = extended_month_date_range(month_period, expand=1)
        in_range = [Q(date__range=[start, end])]
        user = self.request.user
        for c in get_teacher_classes(user, in_range, with_venue=True):
            yield TimetableEvent.create(c, time_zone=user.time_zone)


class CalendarFullView(TeacherOnlyMixin, MonthEventsCalendarView):
    """
    Shows all non-course events and classes filtered by the cities where
    authorized teacher has taught.
    """
    def get_events(self, month_period: MonthPeriod, **kwargs):
        start_date, end_date = extended_month_date_range(month_period, expand=1)
        user = self.request.user
        branches = get_teacher_branches(user, start_date, end_date)
        return get_all_calendar_events(branch_list=branches, start_date=start_date,
                                       end_date=end_date, time_zone=user.time_zone)


class CalendarPersonalView(CalendarFullView):
    """
    Shows all non-course events and classes for courses in which authenticated
    teacher participated.
    """
    calendar_type = 'teacher'
    template_name = "lms/courses/calendar.html"

    def get_events(self, month_period: MonthPeriod, **kwargs):
        start_date, end_date = extended_month_date_range(month_period, expand=1)
        return get_teacher_calendar_events(user=self.request.user,
                                           start_date=start_date,
                                           end_date=end_date)


class CourseListView(PermissionRequiredMixin, generic.ListView):
    model = Course
    context_object_name = 'course_list'
    template_name = "lms/teaching/course_list.html"
    permission_required = AccessTeacherSection.name

    def get_queryset(self):
        course_teachers = Prefetch('course_teachers',
                                   course_teachers_prefetch_queryset(hidden_roles=())
                                   )
        courses = (Course.objects
                   .filter(teachers=self.request.user)
                   .select_related('meta_course', 'semester')
                   .prefetch_related(course_teachers)
                   .order_by('-semester__index', 'meta_course__name'))
        for course in courses:
            course.grouped_teachers = group_teachers(course.course_teachers.all())
        return courses

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['SpectatorRole'] = TeacherRoles.SPECTATOR
        context['CourseDurations'] = CourseDurations
        context['get_student_groups_url'] = get_student_groups_url
        context['CreateCourseNews'] = CreateCourseNews.name
        return context


class GradeBookListView(TeacherOnlyMixin, GradeBookListBaseView):
    template_name = "learning/teaching/gradebook_list.html"

    def get_course_queryset(self):
        qs = super().get_course_queryset()
        return qs.filter(teachers=self.request.user)

    def get_context_data(self, **kwargs):
        tz = self.request.user.time_zone
        current_term_index = get_current_term_pair(tz).index
        # Redirect teacher to the appropriate gradebook page if he has only
        # one course in the current semester.
        for semester in self.object_list:
            if semester.index == current_term_index:
                if len(semester.course_offerings) == 1:
                    course = semester.course_offerings[0]
                    raise Redirect(to=course.get_gradebook_url())
        context = {
            'CourseDurations': CourseDurations,
            "semester_list": self.object_list
        }
        return context


# FIXME: accept enrollment argument and do prefetch_related inside?
# FIXME: enrollment.get_student_assignments?
def _get_total_score(student_assignments: Iterable[StudentAssignment]) -> Decimal:
    total_score = Decimal(0)
    for s in student_assignments:
        if s is not None and s.final_score is not None:
            total_score += s.weighted_final_score
    return normalize_score(total_score)


class CourseStudentProgressView(CourseURLParamsMixin, PermissionRequiredMixin,
                                TemplateView):
    enrollment: Enrollment
    permission_required = ViewEnrollment.name
    template_name = "lms/teaching/student_progress.html"

    def setup(self, request: HttpRequest, **kwargs: Any) -> None:
        super().setup(request, **kwargs)
        queryset = (Enrollment.active
                    .filter(pk=kwargs['enrollment_id'],
                            course=self.course)
                    .select_related("student_profile__user"))
        self.enrollment = get_object_or_404(queryset)
        self.enrollment.course = self.course

    def get_permission_object(self) -> Enrollment:
        return self.enrollment

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        student_assignments = (StudentAssignment.objects
                               .filter(student=self.enrollment.student_profile.user,
                                       assignment__course=self.course)
                               .select_related('assignment', 'assignee__teacher'))
        # TODO: enrollment.total_score
        self.enrollment.total_score = _get_total_score(student_assignments)
        context = {
            "enrollment": self.enrollment,
            "student_assignments": student_assignments
        }
        return context

class TeachingUsefulListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/useful.html"
    permission_required = "teaching.view_faq"

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(self.request.site)
                .with_tag(CurrentInfoBlockTags.TEACHERS_USEFUL)
                .order_by("sort"))
