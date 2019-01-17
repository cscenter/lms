import datetime
from typing import Iterable

from courses.calendar import CalendarEvent
from courses.models import CourseClass
from courses.views import WeekEventsView
from learning.utils import iso_to_gregorian
from learning.views.utils import get_student_city_code
from users.mixins import StudentOnlyMixin


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
