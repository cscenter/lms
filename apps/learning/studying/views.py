from courses.calendar import CalendarEvent
from courses.models import CourseClass
from courses.views import MonthEventsCalendarView
from learning.views.utils import get_student_city_code
from users.mixins import StudentOnlyMixin


class TimetableView(StudentOnlyMixin, MonthEventsCalendarView):
    """
    Shows classes for courses student enrolled in.
    """
    calendar_type = "student"
    template_name = "learning/studying/timetable.html"

    def get_user_city(self):
        return get_student_city_code(self.request)

    def get_events(self, year, month, **kwargs):
        student_city_code = kwargs.get('user_city_code')
        return (CalendarEvent(e) for e in
                self._get_classes(year, month, student_city_code))

    def _get_classes(self, year, month, student_city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .in_city(student_city_code)
                .for_student(self.request.user))
