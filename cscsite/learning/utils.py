import datetime
import re
from collections import namedtuple
from typing import Union, NewType, List

import pytz
from django.conf import settings
from six.moves import zip_longest

import dateutil.parser as dparser
from django.utils import timezone

from core.utils import is_club_site
from learning.settings import SEMESTER_TYPES, FOUNDATION_YEAR, \
    TERMS_INDEX_START, AUTUMN_TERM_START, SUMMER_TERM_START, \
    SPRING_TERM_START, GRADES, POSITIVE_GRADES


CityCode = NewType('CityCode', str)
Timezone = NewType('Timezone', datetime.tzinfo)

TermTuple = namedtuple('TermTuple', ['year', 'type'])

term_types = "|".join(slug for slug, _ in SEMESTER_TYPES)
semester_slug_re = re.compile(r"^(?P<term_year>\d{4})-(?P<term_type>" +
                              term_types + ")$")


def now_local(tz_aware: Union[Timezone, CityCode]) -> datetime.datetime:
    if not isinstance(tz_aware, datetime.tzinfo):
        tz_aware = settings.TIME_ZONES[tz_aware]
    return timezone.localtime(timezone.now(), timezone=tz_aware)


def get_current_term_pair(tz_aware: Union[Timezone, CityCode]):
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
        current_term = SEMESTER_TYPES.spring
    elif summer_term_start <= date < autumn_term_start:
        current_term = SEMESTER_TYPES.summer
    else:
        current_term = SEMESTER_TYPES.autumn
        # Fix year inaccuracy, when spring semester starts later than 1 jan
        if date.month <= spring_term_start.month:
            year -= 1
    return TermTuple(year, current_term)


def convert_term_parts_to_datetime(year, term_start, tz=pytz.UTC):
    dt_naive = dparser.parse(term_start).replace(year=year)
    return tz.localize(dt_naive)


def get_term_start(year, term_type, tz: Timezone):
    """Returns term start point in datetime format."""
    if term_type == SEMESTER_TYPES.spring:
        term_start_str = SPRING_TERM_START
    elif term_type == SEMESTER_TYPES.summer:
        term_start_str = SUMMER_TERM_START
    elif term_type == SEMESTER_TYPES.autumn:
        term_start_str = AUTUMN_TERM_START
    else:
        raise ValueError("get_term_start: unknown term type")
    return convert_term_parts_to_datetime(year, term_start_str, tz)


def get_term_index(target_year, target_term_type):
    """Calculate consecutive term number from spring term of FOUNDATION_YEAR"""
    if target_year < FOUNDATION_YEAR:
        raise ValueError("get_term_index: target year < FOUNDATION_YEAR")
    if target_term_type not in SEMESTER_TYPES:
        raise ValueError("get_term_index: unknown term type %s" %
                         target_term_type)
    terms_in_year = len(SEMESTER_TYPES)
    year_portion = (target_year - FOUNDATION_YEAR) * terms_in_year
    term_portion = TERMS_INDEX_START
    for index, (t, _) in enumerate(SEMESTER_TYPES):
        if t == target_term_type:
            term_portion += index
    return year_portion + term_portion


def get_current_term_index(tz_aware: Union[Timezone, CityCode]):
    return get_term_index(*get_current_term_pair(tz_aware))


def get_term_index_academic_year_starts(year, term_type):
    """
    Returns term index of the beginning of academic year.

    Academic year starts from autumn. Term should be greater than
    autumn of `FOUNDATION_YEAR`.
    """
    if term_type != SEMESTER_TYPES.autumn:
        year -= 1
    return get_term_index(year, SEMESTER_TYPES.autumn)


def get_term_by_index(term_index):
    """Inverse func for `get_term_index`"""
    assert term_index >= TERMS_INDEX_START
    terms_in_year = len(SEMESTER_TYPES)
    term_index -= TERMS_INDEX_START
    year = int(FOUNDATION_YEAR + term_index / terms_in_year)
    term = term_index % terms_in_year
    for index, (t, _) in enumerate(SEMESTER_TYPES):
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


def get_grade_index(grade):
    """
    Returns grade index for easier grades comparison.
    Assume unsatisfactory > not_graded.
    """
    if grade == GRADES.not_graded:
        return 0
    elif grade == GRADES.unsatisfactory:
        return 1
    elif grade == getattr(GRADES, "pass"):
        return 2
    elif grade == GRADES.good:
        return 3
    elif grade == GRADES.excellent:
        return 4
    raise ValueError("Unknown grade type")


def is_positive_grade(grade):
    return grade in POSITIVE_GRADES


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


class LearningPermissionsMixin(object):
    @property
    def _cached_groups(self):
        return set()

    def get_cached_groups(self):
        return self._cached_groups

    @property
    def is_student(self):
        return (self.is_student_center or
                self.is_student_club or
                self.is_volunteer)

    @property
    def is_student_center(self):
        return self.group.STUDENT_CENTER in self._cached_groups

    @property
    def is_student_club(self):
        return self.group.STUDENT_CLUB in self._cached_groups

    @property
    def is_active_student(self):
        if is_club_site():
            return self.is_student_club
        return self.is_student and not self.is_expelled

    @property
    def is_teacher(self):
        return self.is_teacher_center or self.is_teacher_club

    @property
    def is_teacher_club(self):
        return self.group.TEACHER_CLUB in self._cached_groups

    @property
    def is_teacher_center(self):
        return self.group.TEACHER_CENTER in self._cached_groups

    @property
    def is_graduate(self):
        return self.group.GRADUATE_CENTER in self._cached_groups

    @property
    def is_volunteer(self):
        return self.group.VOLUNTEER in self._cached_groups

    @property
    def is_master_student(self):
        """Studying for a masters degree"""
        return self.group.MASTERS_DEGREE in self._cached_groups

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_curator_of_projects(self):
        return self.group.CURATOR_PROJECTS in self._cached_groups

    @property
    def is_interviewer(self):
        return self.group.INTERVIEWER in self._cached_groups

    @property
    def is_project_reviewer(self):
        return self.group.PROJECT_REVIEWER in self._cached_groups
