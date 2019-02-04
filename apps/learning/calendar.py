from itertools import chain

import attr
from django.db.models import Q

from core.utils import is_club_site
from courses.calendar import CalendarEvent
from courses.models import CourseClass
from courses.settings import SemesterTypes
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
               .for_calendar()
               .in_month(year, month)
               .in_cities(cities))

    if for_teacher:
        classes = classes.for_teacher(for_teacher)
    elif for_student:
        classes = classes.for_student(for_student)
    elif is_club_site():
        # Hide summer classes on full calendar
        classes = classes.filter(~Q(course__semester__type=SemesterTypes.SUMMER))

    return chain(
        (CalendarEvent(e) for e in classes),
        (LearningCalendarEvent(e) for e in study_events)
    )
