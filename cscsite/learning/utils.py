import datetime
import itertools

import dateutil.parser as dparser
from django.conf import settings
from django.utils import timezone


def get_current_semester_pair():
    now = timezone.now()
    spring_term_start = (dparser
                         .parse(settings.SPRING_TERM_START)
                         .replace(tzinfo=timezone.utc,
                                  year=now.year))
    autumn_term_start = (dparser
                         .parse(settings.AUTUMN_TERM_START)
                         .replace(tzinfo=timezone.utc,
                                  year=now.year))
    if spring_term_start <= now < autumn_term_start:
        current_season = 'spring'
    else:
        current_season = 'autumn'
    return (now.year, current_season)


def split_list(iterable, pred):
    true_lst, false_lst = [], []
    for x in iterable:
        if pred(x):
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
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)


def co_from_kwargs(kwargs):
    course_slug = kwargs['course_slug']
    semester_slug = kwargs['semester_slug']
    try:
        semester_year, semester_type = semester_slug.split('-')
        semester_year = int(semester_year)
    except ValueError, TypeError:
        raise Http404('Course offering not found')
    return (course_slug, semester_year, semester_type)
