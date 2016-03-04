import datetime
import itertools
from collections import namedtuple

import dateutil.parser as dparser
from django.http import Http404
from django.utils import timezone
from learning.settings import SEMESTER_TYPES, FOUNDATION_YEAR, \
    SEMESTER_INDEX_START, AUTUMN_TERM_START, SUMMER_TERM_START, \
    SPRING_TERM_START

CurrentSemester = namedtuple('CurrentSemester', ['year', 'type'])


def get_current_semester_pair():
    date = timezone.now()
    return date_to_term_pair(date)

def convert_term_start_to_datetime(year, term_start):
    return (dparser
            .parse(term_start)
            .replace(tzinfo=timezone.utc,
                     year=year))

def get_term_start_by_type(term_type):
    # TODO: Replace with something more generic, if you really need to edit this code
    if term_type == SEMESTER_TYPES.spring:
        return SPRING_TERM_START
    elif term_type == SEMESTER_TYPES.summer:
        return SUMMER_TERM_START
    elif term_type == SEMESTER_TYPES.autumn:
        return AUTUMN_TERM_START
    raise ValueError("get_term_start_by_type: unknown term type")

def date_to_term_pair(date):
    assert timezone.is_aware(date)

    year = date.year
    spring_term_start = convert_term_start_to_datetime(year, SPRING_TERM_START)
    autumn_term_start = convert_term_start_to_datetime(year, AUTUMN_TERM_START)
    summer_term_start = convert_term_start_to_datetime(year, SUMMER_TERM_START)

    if spring_term_start <= date < summer_term_start:
        current_term = SEMESTER_TYPES.spring
    elif summer_term_start <= date < autumn_term_start:
        current_term = SEMESTER_TYPES.summer
    else:
        current_term = SEMESTER_TYPES.autumn
        # Fix year inaccuracy, when spring semester starts later than 1 jan
        if date.month <= spring_term_start.month:
            year -= 1
    return CurrentSemester(year, current_term)

def get_semester_index(target_year, semester_type):
    assert target_year >= FOUNDATION_YEAR
    assert semester_type in SEMESTER_TYPES
    index = SEMESTER_INDEX_START
    year = FOUNDATION_YEAR
    # TODO: Optimize by skipping (target_year-FOUNDATION_YEAR) % len(TYPES) and remove infinity loop
    # TODO: add tests
    while True:
        for season, _ in SEMESTER_TYPES:
            if year == target_year and semester_type == season:
                return index
            index += 1
        year += 1
        if year > target_year:
            raise ValueError("get_semester_index: Unreachable target year")

# TODO: get semester pair by index util function




def split_list(iterable, predicate):
    true_lst, false_lst = [], []
    for x in iterable:
        if predicate(x):
            true_lst.append(x)
        else:
            false_lst.append(x)
    return true_lst, false_lst


# Following two functions are taken from
# http://stackoverflow.com/a/1700069/275084
def iso_year_start(iso_year):
    """
    The gregorian calendar date of the first day of the given ISO year
    """
    fourth_jan = datetime.date(iso_year, 1, 4)
    delta = datetime.timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    """
    Gregorian calendar date for the given ISO year, week and day
    """
    year_start = iso_year_start(iso_year)
    return year_start + datetime.timedelta(days=iso_day - 1,
                                           weeks=iso_week - 1)


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks"""
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)


def co_from_kwargs(kwargs):
    course_slug = kwargs['course_slug']
    semester_slug = kwargs['semester_slug']
    try:
        semester_year, semester_type = semester_slug.split('-')
        semester_year = int(semester_year)
    except (ValueError, TypeError):
        raise Http404('Course offering not found')
    return (course_slug, semester_year, semester_type)


class LearningPermissionsMixin(object):
    @property
    def is_student_center(self):
        return False

    @property
    def is_student_club(self):
        return False

    @property
    def is_teacher(self):
        return False

    @property
    def is_student(self):
        return False

    @property
    def is_graduate(self):
        return False

    @property
    def is_volunteer(self):
        return False

    @property
    def is_curator(self):
        return False

# TODO: Add sort order to Semester object and forget about this method!
class SortBySemesterMethodMixin(object):
    @staticmethod
    def sorted(student_projects, reverse=False):
        """Return projects in chronological order"""
        return sorted(student_projects, key=lambda p: p.semester,
                      reverse=reverse)