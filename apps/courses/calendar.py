import datetime
from calendar import Calendar
from collections import defaultdict
from typing import List, Iterable

import attr
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.formats import date_format, time_format
from rest_framework import serializers, fields

from core.settings.base import FOUNDATION_YEAR
from courses.settings import MONDAY_WEEKDAY
from courses.utils import grouper


__all__ = ('EventsCalendar', 'CalendarEvent', 'MonthEventsCalendar',
           'CalendarQueryParams')


@attr.s
class CalendarWeek:
    index: int = attr.ib()  # 1-based
    days: list = attr.ib()


@attr.s
class CalendarDay:
    date: datetime.date = attr.ib()
    events = attr.ib(factory=list)


@attr.s
class CalendarEvent:
    """
    Wrapper for course events to make them look consistent.

    Support: course classes, non-course events
    """
    event = attr.ib()

    @property
    def date(self):
        return self.event.date

    @property
    def type(self):
        return self.event.type

    @property
    def start(self):
        return time_format(self.event.starts_at, "H:i")

    @property
    def end(self):
        return time_format(self.event.ends_at, "H:i")

    @property
    def url(self):
        return self.event.get_absolute_url()

    @property
    def name(self):
        # Avoid circular import
        from learning.models import NonCourseEvent
        if isinstance(self.event, NonCourseEvent):
            return self.event.name
        else:
            return self.event.course.meta_course.name

    @property
    def description(self):
        # In case of course class event it returns class name
        return self.event.name


class EventsCalendar:
    """
    Generates full weeks grid of the month with stored events.

    Note:
        Repeated calls to `_add_events` could broke day events order.

    Usage:
        calendar = EventsCalendar()
        course_class = CourseClass(
            name='Evt1',
            date=datetime.date(year=2018, month=2, day=2),
            starts_at=datetime.time(hour=10, minute=30),
            ends_at=datetime.time(hour=12, minute=0))
        calendar._add_events([CalendarEvent(event=course_class)])
        print(calendar.by_week(2018, 2))
        [
            CalendarWeek(index=5, days=[
                CalendarDay(date=datetime.date(2018, 1, 29), events=[]),
                CalendarDay(date=datetime.date(2018, 1, 30), events=[]),
                CalendarDay(date=datetime.date(2018, 1, 31), events=[]),
                CalendarDay(date=datetime.date(2018, 2, 1), events=[]),
                CalendarDay(date=datetime.date(2018, 2, 2),
                            events=[CalendarEvent(event=<CourseClass: Evt1>)]),
                CalendarDay(date=datetime.date(2018, 2, 3), events=[]),
                CalendarDay(date=datetime.date(2018, 2, 4), events=[])
            ]),
            CalendarWeek(index=6, days=...),
            ...
        ]
    """

    def __init__(self):
        self._date_to_events = defaultdict(list)

    def _add_events(self, events: Iterable[CalendarEvent]):
        # Note: Day events order could be broken on subsequent calls
        events = sorted(events, key=lambda evt: (evt.date, evt.start))
        for event in events:
            self._date_to_events[event.date].append(event)

    def by_week(self, year, month) -> List[CalendarWeek]:
        """
        Return a matrix representing a month's calendar.
        Each row represents a week; week entries are tuple
        (week number, [CalendarDay])
        """
        by_week = []
        cal = Calendar(firstweekday=MONDAY_WEEKDAY)
        dates = cal.itermonthdates(year, month)
        for week in grouper(dates, 7):
            week_number = week[0].isocalendar()[1]
            week_days = []
            for day in week:
                data = CalendarDay(date=day, events=self._date_to_events[day])
                week_days.append(data)
            by_week.append(CalendarWeek(index=week_number, days=week_days))
        return by_week


class MonthEventsCalendar(EventsCalendar):
    def __init__(self, year: int, month: int, events: Iterable[CalendarEvent]):
        super().__init__()
        self.year = year
        self.month = month
        self._date = datetime.date(year, month, 1)
        # TODO: Filter out events from the month or date range for full weeks range?
        self._add_events((e for e in events if
                          e.date.month == month and e.date.year == year))

    @property
    def prev_month(self):
        return self._date + relativedelta(months=-1)

    @property
    def next_month(self):
        return self._date + relativedelta(months=+1)

    @property
    def month_label(self):
        return date_format(self._date, "F Y")

    def weeks(self) -> List[CalendarWeek]:
        """
        Returns a list of the weeks in the month as full weeks.
        Each day of the week stores attached events.
        """
        return super().by_week(self.year, self.month)

    def days(self) -> List[CalendarDay]:
        """Filters out the days which contains any events."""
        by_days = []
        cal = Calendar(firstweekday=MONDAY_WEEKDAY)
        dates = cal.itermonthdates(self.year, self.month)
        for d in dates:
            events = self._date_to_events[d]
            if events:
                day = CalendarDay(date=d, events=events)
                by_days.append(day)
        return by_days


class CalendarQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False, min_value=FOUNDATION_YEAR)
    month = fields.IntegerField(required=False, min_value=1, max_value=12)
    week = fields.IntegerField(required=False, min_value=1)

    def validate_year(self, value):
        today = timezone.now()
        if value > today.year + 1:
            raise ValidationError("Year value too big")
        return value
