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


def get_month_events(year, month, cities, for_teacher=None, for_student=None):
    study_events = (Event.objects
                    .for_calendar()
                    .in_month(year, month)
                    .in_cities(cities))

    classes = (CourseClass.objects
                # FIXME: тут что-то надо сделать с сайтом клуба. Ему нужен user, чтобы отсеять всяких челиков
               .for_calendar()
               .in_month(year, month)
               .in_cities(cities))
    if for_teacher:
        classes = classes.for_teacher(for_teacher)
    elif for_student:
        classes = classes.for_student(for_student)

    return chain(
        (CalendarEvent(e) for e in classes),
        (LearningCalendarEvent(e) for e in study_events)
    )
