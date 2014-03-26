from django.utils import timezone

import dateutil.parser as dparser

from django.conf import settings

# TODO: test this
def get_prev_next_semester_pairs((year, season)):
    if season == 'spring':
        return [(year-1, 'autumn'), (year, 'autumn')]
    else:
        return [(year, 'spring'), (year+1, 'spring')]

def get_current_semester_pair():
    now = timezone.now()
    spring_term_start = (dparser
                         .parse(settings.SPRING_TERM_START)
                         .replace(tzinfo=timezone.utc))
    autumn_term_start = (dparser
                         .parse(settings.AUTUMN_TERM_START)
                         .replace(tzinfo=timezone.utc))
    if spring_term_start <= now < autumn_term_start:
        current_season = 'spring'
    else:
        current_semester = 'autumn'
    return (now.year, current_season)
