from typing import Any, Dict

from django.db.models import Q
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from courses.calendar import TimetableEvent
from courses.models import Course
from courses.services import get_teacher_branches
from courses.utils import MonthPeriod, extended_month_date_range, get_current_term_pair
from courses.views.calendar import MonthEventsCalendarView
from learning.calendar import get_all_calendar_events, get_teacher_calendar_events
from learning.gradebook.views import GradeBookListBaseView
from learning.permissions import CreateCourseNews, ViewTeacherCourses
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
    permission_required = ViewTeacherCourses.name

    def get_queryset(self):
        return (Course.objects
                .filter(teachers=self.request.user)
                .select_related('meta_course', 'semester')
                .prefetch_related('teachers')
                .order_by('-semester__index', 'meta_course__name'))

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
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
            "semester_list": self.object_list
        }
        return context
