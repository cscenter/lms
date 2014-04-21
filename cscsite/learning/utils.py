import datetime

import dateutil.parser as dparser

from django.conf import settings
from django.utils import timezone


# TODO: test this
def get_prev_next_semester_pairs(semester):
    (year, season) = semester
    if season == 'spring':
        return [(year - 1, 'autumn'), (year, 'autumn')]
    else:
        return [(year, 'spring'), (year + 1, 'spring')]


def get_current_semester_pair():
    now = timezone.now()
    spring_term_start = (dparser  # pylint: disable=maybe-no-member
                         .parse(settings.SPRING_TERM_START)
                         .replace(tzinfo=timezone.utc))
    autumn_term_start = (dparser  # pylint: disable=maybe-no-member
                         .parse(settings.AUTUMN_TERM_START)
                         .replace(tzinfo=timezone.utc))
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


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)


## Following two functions are taken from
## http://stackoverflow.com/a/1700069/275084
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
