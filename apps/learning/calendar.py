from typing import List, Iterator

import attr
from django.db.models import Q

from courses.calendar import CalendarEvent
from courses.services import get_teacher_branches
from learning.services import get_student_classes, get_teacher_classes, \
    get_classes, get_study_events


@attr.s
class LearningCalendarEvent(CalendarEvent):
    @property
    def name(self):
        return self.event.name


def _to_range_q_filter(start_date, end_date) -> List[Q]:
    period_filter = []
    if start_date:
        period_filter.append(Q(date__gte=start_date))
    if end_date:
        period_filter.append(Q(date__lte=end_date))
    return period_filter


# FIXME: get_student_events  + CalendarEvent.build(instance) ?
def get_student_calendar_events(*, user, start_date,
                                end_date) -> Iterator[CalendarEvent]:
    period_filter = _to_range_q_filter(start_date, end_date)
    for c in get_student_classes(user, period_filter):
        yield CalendarEvent(c)
    branch_list = [user.branch_id]
    event_filters = [Q(branch__in=branch_list), *period_filter]
    for e in get_study_events(event_filters):
        yield LearningCalendarEvent(e)


def get_teacher_calendar_events(*, user, start_date,
                                end_date) -> Iterator[CalendarEvent]:
    branch_list = get_teacher_branches(user, start_date, end_date)
    period_filter = _to_range_q_filter(start_date, end_date)
    for c in get_teacher_classes(user, period_filter):
        yield CalendarEvent(c)
    event_filters = [Q(branch__in=branch_list), *period_filter]
    for e in get_study_events(event_filters):
        yield LearningCalendarEvent(e)


def get_calendar_events(*, branch_list, start_date, end_date):
    """
    Returns events in a given date range for the given branch list.
    """
    period_filter = _to_range_q_filter(start_date, end_date)
    for c in get_classes(branch_list, period_filter):
        yield CalendarEvent(c)
    event_filters = [Q(branch__in=branch_list), *period_filter]
    for e in get_study_events(event_filters):
        yield LearningCalendarEvent(e)
