import datetime
from abc import ABC
from calendar import Calendar
from collections import defaultdict
from typing import List, Iterable, NewType

import attr
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.formats import date_format, time_format
from django.utils.translation import ugettext_lazy as _
from isoweek import Week
from rest_framework import serializers, fields

from core.utils import chunks
from courses.constants import MONDAY_WEEKDAY, WEEKDAY_TITLES
from courses.utils import MonthPeriod, extended_month_date_range

__all__ = ('EventsCalendar', 'CalendarEvent', 'MonthFullWeeksEventsCalendar',
           'WeekEventsCalendar', 'CalendarQueryParams')


# FIXME: rename. Должно подходить для Class/Assignment/UncategorizedEvent
# TODO: Month calendar has event interface, but timetable is not. Do not use for timetable right now?
@attr.s
class CalendarEvent:
    """
    Wrapper for course events. Supports course classes, non-course events
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
        return self.event.name


@attr.s
class CalendarDay:
    date: datetime.date = attr.ib()
    events: List[CalendarEvent] = attr.ib(factory=list)


@attr.s
class CalendarWeek:
    iso_number: int = attr.ib()  # ISO 8601
    days: List[CalendarDay] = attr.ib()


class EventsCalendar(ABC):
    """
    This class helps to generate days/weeks grid with attached events

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

    def __init__(self, week_starts_on):
        self._date_to_events = defaultdict(list)
        self.week_starts_on = week_starts_on
        self._cal = Calendar(firstweekday=self.week_starts_on)

    def _add_events(self, events: Iterable[CalendarEvent]):
        # Note: Day events order could be broken on subsequent calls
        events = sorted(events, key=lambda evt: (evt.date, evt.start))
        for event in events:
            self._date_to_events[event.date].append(event)

    def week_titles(self):
        return [_(WEEKDAY_TITLES[n]) for n in self._cal.iterweekdays()]

    def _weeks(self, month_period: MonthPeriod) -> List[CalendarWeek]:
        """
        Returns a list of `CalendarWeek` for one month. It contains dates
        outside the specified month since it iterates over complete weeks.
        """
        weeks = []
        dates = self._cal.itermonthdates(month_period.year, month_period.month)
        for full_week in chunks(dates, 7):
            iso_week_number = full_week[0].isocalendar()[1]
            week_days = []
            for day in full_week:
                data = CalendarDay(date=day, events=self._date_to_events[day])
                week_days.append(data)
            weeks.append(CalendarWeek(iso_number=iso_week_number,
                                      days=week_days))
        return weeks

    def _days(self, start: datetime.date,
              end: datetime.date) -> List[CalendarDay]:
        """
        Returns a list of calendar days that have attached events in
        a range [start, end].
        """
        days = []
        for dt in rrule(DAILY, dtstart=start, until=end):
            d = dt.date()
            events = self._date_to_events[d]
            if events:
                day = CalendarDay(date=d, events=events)
                days.append(day)
        return days


# TODO: more generic class DateRangeEventsCalendar? No need right now
class MonthFullWeeksEventsCalendar(EventsCalendar):
    """
    This class extends all non-complete weeks of the month, `.weeks()` or
    `.days()` could return days out of the target month.
    """
    def __init__(self, month_period: MonthPeriod,
                 events: Iterable[CalendarEvent],
                 week_starts_on=MONDAY_WEEKDAY):
        super().__init__(week_starts_on)
        self.month_period = month_period
        begin, end = extended_month_date_range(month_period,
                                               week_start_on=week_starts_on)
        self._add_events((e for e in events if
                          e.date >= begin or e.date <= end))

    @property
    def prev_month(self):
        return self.month_period.starts + relativedelta(months=-1)

    @property
    def next_month(self):
        return self.month_period.starts + relativedelta(months=+1)

    @property
    def month_label(self):
        return date_format(self.month_period.starts, "F Y")

    @property
    def month(self):
        return self.month_period.month

    @property
    def year(self):
        return self.month_period.year

    def weeks(self) -> List[CalendarWeek]:
        """
        Returns a list of the weeks in the month as full weeks.
        Each day of the week stores attached events.
        """
        return super()._weeks(self.month_period)

    def days(self) -> List[CalendarDay]:
        """Returns list of events grouped by day"""
        begin, end = extended_month_date_range(self.month_period,
                                               week_start_on=self.week_starts_on)
        return self._days(begin, end)


ISOWeekNumber = NewType('ISOWeekNumber', int)


# TODO: add week_starts_on support
class WeekEventsCalendar(EventsCalendar):
    def __init__(self, year: int, week_number: ISOWeekNumber,
                 events: Iterable[CalendarEvent],
                 week_starts_on=MONDAY_WEEKDAY):
        super().__init__(week_starts_on)
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
        return self._days(self.week.monday(), self.week.sunday())


class CalendarQueryParams(serializers.Serializer):
    year = fields.IntegerField(required=False,
                               min_value=settings.FOUNDATION_YEAR)
    month = fields.IntegerField(required=False, min_value=1, max_value=12)
    # ISO week-numbering year has 52 or 53 full weeks
    week = fields.IntegerField(required=False, min_value=1, max_value=53)

    def validate_year(self, value):
        today = timezone.now()
        if value > today.year + 1:
            raise ValidationError("Year value is too big")
        return value
