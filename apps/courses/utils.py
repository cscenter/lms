import datetime
import re
from calendar import monthrange
from typing import List, Tuple, NamedTuple

import attr
import pytz
from dateutil import parser as dparser
from django.conf import settings
from django.utils import timezone

from core.timezone import Timezone, now_local
from courses.constants import SemesterTypes, \
    AUTUMN_TERM_START, SPRING_TERM_START, SUMMER_TERM_START, MONDAY_WEEKDAY


class TermIndexError(Exception):
    pass


@attr.s(frozen=True, slots=True)
class TermPair:
    year: int = attr.ib()  # calendar year
    type: str = attr.ib()  # one of `courses.constants.SemesterTypes` values

    @property
    def academic_year(self):
        """
        The academic year begins in autumn and ends during the following summer.
        """
        if self.type != SemesterTypes.AUTUMN:
            return self.year - 1
        return self.year

    @property
    def index(self):
        return get_term_index(self.year, self.type)

    def get_next(self) -> "TermPair":
        return get_term_by_index(self.index + 1)

    def get_prev(self) -> "TermPair":
        return get_term_by_index(self.index - 1)

    def starts_at(self, tz: Timezone):
        return get_term_starts_at(self.year, self.type, tz)


_term_types = r"|".join(slug for slug, _ in SemesterTypes.choices)
semester_slug_re = re.compile(r"^(?P<term_year>\d{4})-(?P<term_type>" +
                              _term_types + r")$")


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


def get_term_index(target_year, target_term_type) -> int:
    """
    Returns 0-based term index.

    Sequence starts from the `settings.FOUNDATION_YEAR` academic year.
    Term order inside academic year is defined by `SemesterTypes` class.
    """
    if target_year < settings.FOUNDATION_YEAR:
        raise ValueError("get_term_index: target year < FOUNDATION_YEAR")
    if target_term_type not in SemesterTypes.values:
        raise ValueError("get_term_index: unknown term type %s" %
                         target_term_type)
    terms_in_year = len(SemesterTypes.choices)
    year_portion = (target_year - settings.FOUNDATION_YEAR) * terms_in_year
    term_portion = 0
    for index, (t, _) in enumerate(SemesterTypes.choices):
        if t == target_term_type:
            term_portion += index
    return year_portion + term_portion


def get_term_by_index(term_index) -> TermPair:
    """Inverse func for `get_term_index`"""
    if term_index < 0:
        raise TermIndexError()
    terms_in_year = len(SemesterTypes.choices)
    year = int(settings.FOUNDATION_YEAR + term_index / terms_in_year)
    term = term_index % terms_in_year
    for index, (t, _) in enumerate(SemesterTypes.choices):
        if index == term:
            return TermPair(year, t)


def get_boundaries(year, month) -> Tuple:
    """
    Calculates closed interval in days for complete weeks of the month
    and returns boundaries of this interval.

    Example:
        In: get_boundaries(2018, 2)
        Out: (datetime.date(2018, 1, 29), datetime.date(2018, 3, 4))
        # Calculate date for the first day of the first week in the month
        first_day = datetime.date(year=2018, month=2, day=1)
        # first_day.weekday() is 3 (0-based index)
        lower_bound = first_day - datetime.timedelta(days=3)
        datetime.date(year=2018, month=1, day=29)
        # The same logic to calculate upper bound (the last day of the last
        # complete week of the month)
    """
    day1, days_in_month = monthrange(year, month)
    date = datetime.date(year, month, 1)
    # Go back to the beginning of the week
    days_before = (day1 - MONDAY_WEEKDAY) % 7
    days_after = (MONDAY_WEEKDAY - day1 - days_in_month) % 7
    start = date - datetime.timedelta(days=days_before)
    end = date + datetime.timedelta(days=days_in_month + days_after - 1)
    return start, end


def get_terms_for_calendar_month(year: int, month: int) -> List[TermPair]:
    start_date, end_date = get_boundaries(year, month)
    # Case date to timezone aware datetime, no matter which timezone we choose
    time_part = datetime.time(tzinfo=pytz.UTC)
    start_aware = datetime.datetime.combine(start_date, time_part)
    end_aware = datetime.datetime.combine(end_date, time_part)
    start_term = date_to_term_pair(start_aware)
    end_term = date_to_term_pair(end_aware)
    if start_term.type != end_term.type:
        return [start_term, end_term]
    else:
        return [start_term]


def execution_time_string(value: datetime.timedelta):
    minutes = int(value.total_seconds()) // 60
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}"
