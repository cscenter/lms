from itertools import chain

import attr

from courses.calendar import CalendarEvent
from courses.models import CourseClass
from learning.models import Event


@attr.s
class LearningCalendarEvent(CalendarEvent):
    @property
    def name(self):
        return self.event.name


def get_month_events(year, month, cities):
    study_events = (Event.objects
                    .for_calendar()
                    .in_month(year, month)
                    .in_cities(cities))

    classes = (CourseClass.objects
    # FIXME: removed club crutch
               .for_calendar()
               .in_month(year, month)
               .in_cities(cities))

    return chain(
        (CalendarEvent(e) for e in classes(year, month, cities)),
        (LearningCalendarEvent(e) for e in study_events(year, month))
    )




"""
city_code - 'student city code'
    @staticmethod
    def _get_events(year, month, city_code):
        return (Event.objects
                .for_calendar()
                .for_city(city_code)
                .in_month(year, month))

    def _get_classes(self, year, month, city_code):
        return (CourseClass.objects
                .for_calendar(self.request.user)
                .in_month(year, month)
                .in_city(city_code))
"""