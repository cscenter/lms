import datetime
from calendar import Calendar
from collections import defaultdict
from typing import List, Iterable, NewType

import attr
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.formats import date_format, time_format
from isoweek import Week
from rest_framework import serializers, fields

from core.settings.base import FOUNDATION_YEAR
from courses.constants import MONDAY_WEEKDAY
from core.utils import chunks

__all__ = ('EventsCalendar', 'CalendarEvent', 'MonthEventsCalendar',
           'WeekEventsCalendar', 'CalendarQueryParams')


@attr.s
class CalendarDay:
    date: datetime.date = attr.ib()
    events = attr.ib(factory=list)


@attr.s
class CalendarWeek:
    iso_number: int = attr.ib()  # ISO 8601
    days: List[CalendarDay] = attr.ib()


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
        Returns a matrix representing a month's calendar.
        Each row represents a week; week entries are tuple
        (week number, [CalendarDay])
        """
        by_week = []
        cal = Calendar(firstweekday=MONDAY_WEEKDAY)
        dates = cal.itermonthdates(year, month)
        for full_week in chunks(dates, 7):
            iso_week_number = full_week[0].isocalendar()[1]
            week_days = []
            for day in full_week:
                data = CalendarDay(date=day, events=self._date_to_events[day])
                week_days.append(data)
            by_week.append(CalendarWeek(iso_number=iso_week_number,
                                        days=week_days))
        return by_week

    def by_day(self, start: datetime.date,
               end: datetime.date) -> List[CalendarDay]:
        """
        Filters out the days in a range [start, end] which contains any event.
        """
        by_days = []
        for dt in rrule(DAILY, dtstart=start, until=end):
            d = dt.date()
            events = self._date_to_events[d]
            if events:
                day = CalendarDay(date=d, events=events)
                by_days.append(day)
        return by_days


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
        """Returns attached events in the month grouped by day"""
        # FIXME: contains days from all full weeks in the month
        # FIXME: сейчас используется на странице препода (там list view), кажется, в таком случае показывать предыдущие даты не совсем уместно
        cal = Calendar(firstweekday=MONDAY_WEEKDAY)
        dates = cal.itermonthdates(self.year, self.month)
        first = last = next(dates)
        for last in dates:
            pass
        return self.by_day(first, last)


ISOWeekNumber = NewType('ISOWeekNumber', int)


class WeekEventsCalendar(EventsCalendar):
    def __init__(self, year: int, week_number: ISOWeekNumber,
                 events: Iterable[CalendarEvent]):
        super().__init__()
        w = Week(year, week_number)
        self._add_events((e for e in events if
                          w.monday() <= e.date <= w.sunday()))
        self.week = w

    @property
    def week_label(self):
        monday = self.week.monday()
        sunday = self.week.sunday()
        if monday.month == sunday.month:
            start_format = "d"
            end_format = "d E Y"
        else:
            start_format = "d b"
            end_format = "d b Y"
        start = date_format(monday, start_format)
        end = date_format(sunday, end_format)
        return f"{start}–{end}"

    @property
    def prev_week(self) -> Week:
        """Returns ISO 8601 compatible week object"""
        return self.week - 1

    @property
    def next_week(self) -> Week:
        """Returns ISO 8601 compatible week object"""
        return self.week + 1

    def days(self) -> List[CalendarDay]:
        return self.by_day(self.week.monday(), self.week.sunday())


class CalendarQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False, min_value=FOUNDATION_YEAR)
    month = fields.IntegerField(required=False, min_value=1, max_value=12)
    # ISO week-numbering year has 52 or 53 full weeks
    week = fields.IntegerField(required=False, min_value=1, max_value=53)

    def validate_year(self, value):
        today = timezone.now()
        if value > today.year + 1:
            raise ValidationError("Year value is too big")
        return value
