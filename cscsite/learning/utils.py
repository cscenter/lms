import datetime
from collections import namedtuple
from six.moves import zip_longest

import dateutil.parser as dparser
from django.http import Http404
from django.utils import timezone
from learning.settings import SEMESTER_TYPES, FOUNDATION_YEAR, \
    TERMS_INDEX_START, AUTUMN_TERM_START, SUMMER_TERM_START, \
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


def get_term_start(year, term_type):
    """Returns term start point in datetime format"""
    if term_type == SEMESTER_TYPES.spring:
        term_start_str = SPRING_TERM_START
    elif term_type == SEMESTER_TYPES.summer:
        term_start_str = SUMMER_TERM_START
    elif term_type == SEMESTER_TYPES.autumn:
        term_start_str = AUTUMN_TERM_START
    else:
        raise ValueError("get_term_start: unknown term type")
    return convert_term_start_to_datetime(year, term_start_str)


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


def get_term_index_academic(year, term_type, rewind_years):
    """
    Subtracts N academic years from `end_year` and returns term index
    of the beginning of calculated academic year.
    Academic year starts from autumn.

    Not properly works for FOUNDATION_YEAR spring and summer, but I believe
    it's not really necessary.
    """
    assert rewind_years > 0
    if term_type == SEMESTER_TYPES.autumn:
        target_year = year - rewind_years + 1
    else:
        target_year = year - rewind_years
    return get_term_index(target_year, SEMESTER_TYPES.autumn)


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
    return zip_longest(fillvalue=fillvalue, *args)


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
    def is_master(self):
        return False

    @property
    def is_curator(self):
        return False

    @property
    def is_interviewer(self):
        return False

    @property
    def is_project_reviewer(self):
        return False
