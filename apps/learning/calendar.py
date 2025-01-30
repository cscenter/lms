from typing import Iterator, List

from django.db.models import Q

from courses.calendar import CalendarEvent, CalendarEventFactory
from courses.services import get_teacher_branches
from learning.selectors import (
    get_classes, get_student_classes, get_study_events, get_teacher_classes
)
from users.models import StudentProfile


def _to_range_q_filter(start_date, end_date) -> List[Q]:
    period_filter = []
    if start_date:
        period_filter.append(Q(date__gte=start_date))
    if end_date:
        period_filter.append(Q(date__lte=end_date))
    return period_filter


# FIXME: get_student_events  + CalendarEvent.build(instance) ?
def get_student_calendar_events(*, student_profile: StudentProfile,
                                start_date, end_date) -> Iterator[CalendarEvent]:
    period_filter = _to_range_q_filter(start_date, end_date)
    user = student_profile.user
    for c in get_student_classes(user, period_filter):
        yield CalendarEventFactory.create(c, time_zone=user.time_zone)
    branch_list = [student_profile.branch_id]
    event_filters = [Q(branch__in=branch_list), *period_filter]
    for e in get_study_events(event_filters):
        yield CalendarEventFactory.create(e)


def get_teacher_calendar_events(*, user, start_date,
                                end_date) -> Iterator[CalendarEvent]:
    period_filter = _to_range_q_filter(start_date, end_date)
    for c in get_teacher_classes(user, period_filter):
        yield CalendarEventFactory.create(c, time_zone=user.time_zone)
    branch_list = get_teacher_branches(user, start_date, end_date)
    event_filters = [Q(branch__in=branch_list), *period_filter]
    for e in get_study_events(event_filters):
        yield CalendarEventFactory.create(e)


def get_all_calendar_events(*, branch_list, start_date, end_date, time_zone):
    """
    Returns events in a given date range for the given branch list.
    """
    period_filter = _to_range_q_filter(start_date, end_date)
    class_filters = [Q(course__is_draft=False), *period_filter]
    for c in get_classes(branch_list, class_filters):
        yield CalendarEventFactory.create(c, time_zone=time_zone)
    event_filters = [Q(branch__in=branch_list), *period_filter]
    for e in get_study_events(event_filters):
        yield CalendarEventFactory.create(e)
