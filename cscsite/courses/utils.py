import datetime
import re
from collections import namedtuple
from typing import Union, List

import pytz
from dateutil import parser as dparser
from django.utils import timezone

from courses.settings import SemesterTypes, TERMS_INDEX_START
from learning.settings import SPRING_TERM_START, AUTUMN_TERM_START, \
    SUMMER_TERM_START
from core.settings.base import FOUNDATION_YEAR
from learning.utils import Timezone, CityCode, now_local

TermTuple = namedtuple('TermTuple', ['year', 'type'])


def get_current_term_pair(tz_aware: Union[Timezone, CityCode]) -> TermTuple:
    dt_local = now_local(tz_aware)
    return date_to_term_pair(dt_local)


def date_to_term_pair(date):
    assert timezone.is_aware(date)
    year = date.year
    # Term start should be aware of the same timezone as `date`
    _convert = convert_term_parts_to_datetime
    spring_term_start = _convert(year, SPRING_TERM_START, date.tzinfo)
    autumn_term_start = _convert(year, AUTUMN_TERM_START, date.tzinfo)
    summer_term_start = _convert(year, SUMMER_TERM_START, date.tzinfo)

    if spring_term_start <= date < summer_term_start:
        current_term = SemesterTypes.SPRING
    elif summer_term_start <= date < autumn_term_start:
        current_term = SemesterTypes.SUMMER
    else:
        current_term = SemesterTypes.AUTUMN
        # Fix year inaccuracy, when spring semester starts later than 1 jan
        if date.month <= spring_term_start.month:
            year -= 1
    return TermTuple(year, current_term)


def convert_term_parts_to_datetime(year, term_start,
                                   tz=pytz.UTC) -> datetime.datetime:
    dt_naive = dparser.parse(term_start).replace(year=year)
    return tz.localize(dt_naive)


def get_term_start(year, term_type, tz: Timezone) -> datetime.datetime:
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


def next_term_starts_at(term_index=None,
                        tz_aware=pytz.UTC) -> datetime.datetime:
    if not term_index:
        term_index = get_current_term_index(tz_aware)
    year, next_term = get_term_by_index(term_index + 1)
    return get_term_start(year, next_term, tz_aware)


def get_term_index(target_year, target_term_type):
    """Calculate consecutive term number from spring term of FOUNDATION_YEAR"""
    if target_year < FOUNDATION_YEAR:
        raise ValueError("get_term_index: target year < FOUNDATION_YEAR")
    if target_term_type not in SemesterTypes.values:
        raise ValueError("get_term_index: unknown term type %s" %
                         target_term_type)
    terms_in_year = len(SemesterTypes.choices)
    year_portion = (target_year - FOUNDATION_YEAR) * terms_in_year
    term_portion = TERMS_INDEX_START
    for index, (t, _) in enumerate(SemesterTypes.choices):
        if t == target_term_type:
            term_portion += index
    return year_portion + term_portion


def get_current_term_index(tz_aware: Union[Timezone, CityCode]):
    return get_term_index(*get_current_term_pair(tz_aware))


def get_term_index_academic_year_starts(year: int, term_type):
    """
    Returns term index of the beginning of academic year.

    Academic year starts from autumn. Term should be greater than
    autumn of `FOUNDATION_YEAR`.
    """
    if term_type != SemesterTypes.AUTUMN:
        year -= 1
    return get_term_index(year, SemesterTypes.AUTUMN)


def get_term_by_index(term_index):
    """Inverse func for `get_term_index`"""
    assert term_index >= TERMS_INDEX_START
    terms_in_year = len(SemesterTypes.choices)
    term_index -= TERMS_INDEX_START
    year = int(FOUNDATION_YEAR + term_index / terms_in_year)
    term = term_index % terms_in_year
    for index, (t, _) in enumerate(SemesterTypes.choices):
        if index == term:
            term = t
    assert not isinstance(term, int)
    return year, term


def get_terms_for_calendar_month(year: int, month: int) -> List[TermTuple]:
    from learning.calendar import get_bounds_for_calendar_month
    start_date, end_date = get_bounds_for_calendar_month(year, month)
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


term_types = "|".join(slug for slug, _ in SemesterTypes.choices)
semester_slug_re = re.compile(r"^(?P<term_year>\d{4})-(?P<term_type>" +
                              term_types + ")$")