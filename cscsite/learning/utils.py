import datetime
import itertools
from collections import namedtuple

import dateutil.parser as dparser
from django.conf import settings
from django.http import Http404
from django.utils import timezone

from .constants import SEMESTER_TYPES

CurrentSemester = namedtuple('CurrentSemester', ['year', 'type'])


def get_current_semester_pair():
    date = timezone.now()
    return date_to_semester_pair(date)

def date_to_semester_pair(date):
    assert timezone.is_aware(date)
    spring_term_start = (dparser
                         .parse(settings.SPRING_TERM_START)
                         .replace(tzinfo=timezone.utc,
                                  year=date.year))
    autumn_term_start = (dparser
                         .parse(settings.AUTUMN_TERM_START)
                         .replace(tzinfo=timezone.utc,
                                  year=date.year))
    summer_term_start = (dparser
                         .parse(settings.SUMMER_TERM_START)
                         .replace(tzinfo=timezone.utc,
                                  year=date.year))
    year = date.year
    if spring_term_start <= date < summer_term_start:
        current_season = SEMESTER_TYPES.spring
    elif summer_term_start <= date < autumn_term_start:
        current_season = SEMESTER_TYPES.summer
    else:
        current_season = SEMESTER_TYPES.autumn
        # Fix year inaccuracy, when spring semester starts later than 1 jan
        if date.month <= spring_term_start.month:
            year -= 1
    return CurrentSemester(year, current_season)



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
    def is_graduate(self):
        return False

    @property
    def is_volunteer(self):
        return False

    @property
    def is_curator(self):
        return False