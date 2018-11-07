import datetime
import re
from collections import namedtuple
from typing import Union, NewType, List

import dateutil.parser as dparser
import pytz
from django.conf import settings
from django.utils import timezone
from six.moves import zip_longest

from learning.settings import FOUNDATION_YEAR, \
    AUTUMN_TERM_START, SUMMER_TERM_START, \
    SPRING_TERM_START, GradeTypes
from courses.settings import SemesterTypes, TERMS_INDEX_START

CityCode = NewType('CityCode', str)
Timezone = NewType('Timezone', datetime.tzinfo)

TermTuple = namedtuple('TermTuple', ['year', 'type'])

term_types = "|".join(slug for slug, _ in SemesterTypes.choices)
semester_slug_re = re.compile(r"^(?P<term_year>\d{4})-(?P<term_type>" +
                              term_types + ")$")


def now_local(tz_aware: Union[Timezone, CityCode]) -> datetime.datetime:
    if not isinstance(tz_aware, datetime.tzinfo):
        tz_aware = settings.TIME_ZONES[tz_aware]
    return timezone.localtime(timezone.now(), timezone=tz_aware)


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


def grade_to_mark(grade):
    """
    Converts grade to the mark analog for easier grades comparison.

    Assume unsatisfactory > not_graded.
    """
    if grade == GradeTypes.NOT_GRADED:
        return 0
    elif grade == GradeTypes.UNSATISFACTORY:
        return 1
    elif grade == GradeTypes.CREDIT:
        return 2
    elif grade == GradeTypes.GOOD:
        return 3
    elif grade == GradeTypes.EXCELLENT:
        return 4
    raise ValueError("Unknown grade type")


def is_negative_grade(grade):
    return grade == GradeTypes.UNSATISFACTORY


def split_on_condition(iterable, predicate):
    true_lst, false_lst = [], []
    for x in iterable:
        if predicate(x):
            true_lst.append(x)
        else:
            false_lst.append(x)
    return true_lst, false_lst


# Following two functions are taken from
# http://stackoverflow.com/a/1700069/275084
def iso_year_start(iso_year) -> datetime.date:
    """
    The gregorian calendar date of the first day of the given ISO year
    """
    fourth_jan = datetime.date(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day) -> datetime.date:
    """
    Gregorian calendar date for the given ISO year, week and day
    """
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(days=iso_day - 1,
                                           weeks=iso_week - 1)


def grouper(iterable, n, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks:
    Example:
        In: grouper('ABCDEFG', 3, 'x')
        Out: ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)
