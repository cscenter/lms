from courses.calendar import CalendarEvent
from courses.models import CourseClass
from courses.views.calendar import MonthEventsCalendarView
from learning.views.utils import get_teacher_city_code
from users.mixins import TeacherOnlyMixin


class TimetableView(TeacherOnlyMixin, MonthEventsCalendarView):
    """
    Shows classes for courses where authorized teacher participate in.
    """
    calendar_type = "teacher"
    template_name = "learning/teaching/timetable.html"

    def get_default_timezone(self):
        return get_teacher_city_code(self.request)

    def get_events(self, year, month, **kwargs):
        qs = (CourseClass.objects
              .in_month(year, month)
              .filter(course__teachers=self.request.user)
              .for_timetable(self.request.user))
        return (CalendarEvent(e) for e in qs)
