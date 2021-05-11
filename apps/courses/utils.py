import datetime
from calendar import monthrange
from dataclasses import dataclass, field
from typing import Iterator

import attr
import pytz
from dateutil import parser as dparser

from django.conf import settings
from django.utils import timezone

from core.timezone import Timezone, now_local
from courses.constants import (
    AUTUMN_TERM_START, MONDAY_WEEKDAY, SPRING_TERM_START, SUMMER_TERM_START,
    SemesterTypes
)


class TermIndexError(Exception):
    pass


@attr.s(eq=True, order=True, frozen=True, slots=True)
class TermPair:
    index: int = attr.ib(init=False, repr=False)
    year: int = attr.ib(eq=False, order=False)
    type: str = attr.ib(eq=False, order=False)

    def __attrs_post_init__(self):
        if self.type not in SemesterTypes.values:
            raise ValueError("TermPair: unsupported `type` value")
        object.__setattr__(self, 'index', get_term_index(self.year, self.type))

    @property
    def academic_year(self):
        """
        The academic year begins in autumn and ends during the following summer.
        """
        if self.type != SemesterTypes.AUTUMN:
            return self.year - 1
        return self.year

    @property
    def slug(self) -> str:
        return f"{self.year}-{self.type}"

    @property
    def label(self) -> str:
        return "{0} {1}".format(SemesterTypes.values[self.type], self.year)

    def get_next(self) -> "TermPair":
        return get_term_by_index(self.index + 1)

    def get_prev(self) -> "TermPair":
        return get_term_by_index(self.index - 1)

    def starts_at(self, tz: Timezone):
        return get_term_starts_at(self.year, self.type, tz)


@dataclass
class MonthPeriod:
    year: int
    month: int
    starts: datetime.date = field(init=False)
    ends: datetime.date = field(init=False)

    def __post_init__(self):
        weekday, days_in_month = monthrange(self.year, self.month)
        self.starts = datetime.date(self.year, self.month, 1)
        self.ends = self.starts + datetime.timedelta(days=days_in_month - 1)


def date_to_term_pair(dt: datetime.datetime) -> TermPair:
    """
    Converts aware datetime to `(year, term type)` tuple
    Example:
        tz = pytz.timezone('Europe/Moscow')
        dt_naive = datetime.datetime(2018, month=11, day=1, hour=23, minute=59)
        dt_aware = tz.localize(dt_naive)
        date_to_term_pair(dt_aware)  # TermPair(year=2018, type='autumn')
    """
    assert timezone.is_aware(dt)
    year = dt.year
    # Term start should be aware of the same timezone as `date`
    _convert = convert_term_parts_to_datetime
    spring_term_start = _convert(year, SPRING_TERM_START, dt.tzinfo)
    autumn_term_start = _convert(year, AUTUMN_TERM_START, dt.tzinfo)
    summer_term_start = _convert(year, SUMMER_TERM_START, dt.tzinfo)

    if spring_term_start <= dt < summer_term_start:
        current_term = SemesterTypes.SPRING
    elif summer_term_start <= dt < autumn_term_start:
        current_term = SemesterTypes.SUMMER
    else:
        current_term = SemesterTypes.AUTUMN
        # Fix year inaccuracy, when spring semester starts later than 1 jan
        if dt.month <= spring_term_start.month:
            year -= 1
    return TermPair(year, current_term)


def get_current_term_pair(tz: Timezone = settings.DEFAULT_TIMEZONE) -> TermPair:
    dt_local = now_local(tz)
    return date_to_term_pair(dt_local)


def convert_term_parts_to_datetime(year, term_start,
                                   tz=pytz.UTC) -> datetime.datetime:
    dt_naive = dparser.parse(term_start).replace(year=year)
    return tz.localize(dt_naive)


def get_term_starts_at(year, term_type, tz: Timezone) -> datetime.datetime:
    """Returns term start point in datetime format."""
    if term_type == SemesterTypes.SPRING:
        term_start_str = SPRING_TERM_START
    elif term_type == SemesterTypes.SUMMER:
        term_start_str = SUMMER_TERM_START
    elif term_type == SemesterTypes.AUTUMN:
        term_start_str = AUTUMN_TERM_START
    else:
        raise ValueError("get_term_start: unknown term type")
    return convert_term_parts_to_datetime(year, term_start_str, tz)


_FIRST_TERM_YEAR = 1980


def get_term_index(term_year, term_type) -> int:
    """
    Returns 0-based term index.

    Term order inside academic year is defined by `SemesterTypes` class.
    """
    if term_year < _FIRST_TERM_YEAR:
        raise ValueError(f"get_term_index: target year < {_FIRST_TERM_YEAR}")
    if term_type not in SemesterTypes.values:
        raise ValueError("get_term_index: unknown term type %s" % term_type)
    terms_in_year = len(SemesterTypes.choices)
    year_portion = (term_year - _FIRST_TERM_YEAR) * terms_in_year
    term_portion = 0
    for index, (t, _) in enumerate(SemesterTypes.choices):
        if t == term_type:
            term_portion += index
    return year_portion + term_portion


def get_term_by_index(term_index) -> TermPair:
    """Inverse func for `get_term_index`"""
    if term_index < 0:
        raise TermIndexError()
    terms_in_year = len(SemesterTypes.choices)
    year = int(_FIRST_TERM_YEAR + term_index / terms_in_year)
    term = term_index % terms_in_year
    for index, (t, _) in enumerate(SemesterTypes.choices):
        if index == term:
            return TermPair(year, t)


def get_terms_in_range(start: datetime.date,
                       end: datetime.date) -> Iterator[TermPair]:
    time_part = datetime.time(tzinfo=pytz.UTC)
    start_utc = datetime.datetime.combine(start, time_part)
    end_utc = datetime.datetime.combine(end, time_part)
    start_term = date_to_term_pair(start_utc)
    end_term = date_to_term_pair(end_utc)
    current = start_term
    while current.index <= end_term.index:
        yield current
        current = current.get_next()


def execution_time_string(value: datetime.timedelta):
    minutes = int(value.total_seconds()) // 60
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}"


def extended_month_date_range(month_period: MonthPeriod,
                              week_start_on=MONDAY_WEEKDAY,
                              expand: int = 0):
    """
    Returns date range (the first day of the first week of the month,
    the last day of the last week of the month) expanded by *expand* days.
    """
    start_date = get_start_of_week(month_period.starts, week_start_on)
    end_date = get_end_of_week(month_period.ends, week_start_on)
    if expand:
        start_date -= datetime.timedelta(days=expand)
        end_date += datetime.timedelta(days=expand)
    return start_date, end_date


def get_start_of_week(value: datetime.date, week_start_on=MONDAY_WEEKDAY) -> datetime.date:
    """
    Returns the first day of the week. By default week starts on Monday.
    """
    weekday = value.weekday()  # 0 - 6
    days_diff = (weekday - week_start_on) % 7
    return value - datetime.timedelta(days=days_diff)


def get_end_of_week(value: datetime.date, week_start_on=MONDAY_WEEKDAY) -> datetime.date:
    """
    Returns the last day of the week. By default week starts on Monday.
    """
    first_day = get_start_of_week(value, week_start_on)
    return first_day + datetime.timedelta(days=6)
