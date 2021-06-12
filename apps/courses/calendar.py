import datetime
from abc import ABC
from calendar import Calendar
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, List, NewType

import attr
from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule
from isoweek import Week

from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from core.timezone.typing import Timezone
from core.utils import chunks
from courses.constants import MONDAY_WEEKDAY, WEEKDAY_TITLES
from courses.models import Course, CourseClass, LearningSpace
from courses.utils import MonthPeriod, extended_month_date_range

__all__ = ('CalendarEvent', 'TimetableEvent', 'CalendarEventFactory',
           'EventsCalendar', 'MonthFullWeeksEventsCalendar',
           'WeekEventsCalendar')

from learning.models import Event

ISOWeekNumber = NewType('ISOWeekNumber', int)


@dataclass(eq=True, frozen=True)
class CalendarEvent:
    type: str
    date: datetime.date
    starts_at: datetime.time
    ends_at: datetime.time
    name: str
    description: str
    url: str


@dataclass(eq=True, frozen=True)
class TimetableEvent(CalendarEvent):
    course: Course
    venue: LearningSpace

    @classmethod
    def create(cls, course_class: CourseClass, time_zone: Timezone):
        starts_at = course_class.starts_at_local(tz=time_zone)
        ends_at = course_class.ends_at_local(tz=time_zone)
        return cls(type=course_class.type,
                   name=course_class.name,
                   description=course_class.name,
                   url=course_class.get_absolute_url(),
                   date=starts_at.date(),
                   starts_at=starts_at.time(),
                   ends_at=ends_at.time(),
                   course=course_class.course,
                   venue=course_class.venue)


class CalendarEventFactory:
    @classmethod
    def create(cls, instance, **kwargs):
        # FIXME: Consider to use abstract factory class instead before add new class here
        if isinstance(instance, CourseClass):
            return cls._from_course_class(instance, **kwargs)
        elif isinstance(instance, Event):
            return cls._from_generic_event(instance, **kwargs)
        raise ValueError(f"{instance.__class__} is not supported")

    @classmethod
    def _from_course_class(cls, course_class: CourseClass, time_zone: Timezone,
                           url_builder: Callable = None, **kwargs):
        if url_builder:
            url = url_builder(course_class)
        else:
            url = course_class.get_absolute_url()
        starts_at = course_class.starts_at_local(tz=time_zone)
        ends_at = course_class.ends_at_local(tz=time_zone)
        return CalendarEvent(type=course_class.type,
                             name=course_class.course.meta_course.name,
                             description=course_class.name,
                             url=url,
                             date=starts_at.date(),
                             starts_at=starts_at.time(),
                             ends_at=ends_at.time())

    @classmethod
    def _from_generic_event(cls, instance: Event, **kwargs):
        return CalendarEvent(name=instance.name,
                             description=instance.name,
                             url=instance.get_absolute_url(),
                             date=instance.date,
                             starts_at=instance.starts_at,
                             ends_at=instance.ends_at,
                             type=instance.type)


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
        events = sorted(events, key=lambda evt: (evt.date, evt.starts_at))
        for event in events:
            self._date_to_events[event.date].append(event)

    @property
    def week_titles(self):
        return [_(WEEKDAY_TITLES[n]) for n in self._cal.iterweekdays()]

    def _weeks(self, month_period: MonthPeriod) -> List[CalendarWeek]:
        """
        Returns a list of complete `CalendarWeek`s for the requested month.

        Note:
            Complete week could contain dates outside the specified month.
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

    # TODO: return full range with an empty event list
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
    This class extends all non-complete weeks of the month, `.weeks` or
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

    @property
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
