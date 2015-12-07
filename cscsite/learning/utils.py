import csv
import datetime
import itertools
import logging
from math import ceil

import dateutil.parser as dparser
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


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
    summer_term_start = (dparser
                         .parse(settings.SUMMER_TERM_START)
                         .replace(tzinfo=timezone.utc,
                                  year=now.year))
    if spring_term_start <= now < summer_term_start:
        current_season = 'spring'
    elif summer_term_start <= now < autumn_term_start:
        current_season = 'summer'
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


def import_stepic(request, selected_assignment):
    from learning.models import AssignmentStudent, Assignment
    from users.models import CSCUser

    def update_score(assignment_id, user, score):
        try:
            a_s = (AssignmentStudent.objects
                   .get(assignment__pk=assignment_id, student=user))
        except ObjectDoesNotExist:
            logger.debug("User ID {} with stepic ID {} doesn't "
                         "have an assignment {}"
                         .format(user.pk, user.stepic_id, assignment_id))
            return False
        a_s.grade = score
        a_s.save()
        return True

    f = request.FILES['csvfile']
    reader = csv.DictReader(iter(f), fieldnames=['user_id'], restkey='as_ids')
    total = 0
    success = 0
    response = {'success': 0, 'total': 0, 'errors': []}
    # skip real headers
    reader.next()
    headers = ['user_id', selected_assignment.pk]
    for entry in reader:
        total += len(headers) - 1
        stepic_id = int(entry['user_id'])
        try:
            user = CSCUser.objects.get(stepic_id=stepic_id)
        except ObjectDoesNotExist:
            msg = _("No user with Stepic ID {}").format(stepic_id)
            logger.debug(msg)
            messages.error(request, msg)
            continue
        for assignment_id, score in zip(headers[1:], entry[reader.restkey]):
            stepic_points = int(ceil(float(score)))
            res = update_score(int(assignment_id), user, stepic_points)
            success += int(res)
            logger.debug("Wrote {} points for user {} on assignment {}"
                         .format(stepic_points, user.pk, assignment_id))
    logger.debug("{}/{} successes".format(success, total))
    response['success'], response['total'] = success, total
    return response


def import_yandex(request, selected_assignment):
    from learning.models import AssignmentStudent, Assignment
    from users.models import CSCUser

    assignment_id = int(selected_assignment.pk)
    assert assignment_id > 0

    def update_score(assignment_id, user, score):
        try:
            a_s = (AssignmentStudent.objects
                   .get(assignment__pk=assignment_id, student=user))
        except ObjectDoesNotExist:
            logger.debug("User ID {} with Yandex ID {} doesn't "
                         "have an assignment {}"
                         .format(user.pk, user.stepic_id, assignment_id))
            return False
        a_s.grade = score
        a_s.save()
        return True


    f = request.FILES['csvfile']
    reader = csv.DictReader(iter(f))
    total = 0
    success = 0
    response = {'success': 0, 'total': 0, 'errors': []}
    # skip real headers
    headers = reader.next()
    if "login" not in headers or "total" not in headers:
        messages.error(request, "ERROR: `login` or `total` header not found")
        return response

    for row in reader:
        total += 1
        yandex_id = row['login'].strip()
        try:
            user = CSCUser.objects.get(yandex_id__iexact=yandex_id)
        except ObjectDoesNotExist:
            msg = _("No user with Yandex ID {}").format(yandex_id)
            logger.debug(msg)
            messages.error(request, msg)
            continue
        except MultipleObjectsReturned:
            msg = _("Multiple user with Yandex ID {}").format(yandex_id)
            messages.error(request, msg)
            continue

        points = int(ceil(float(row['total'])))
        res = update_score(assignment_id, user, points)
        success += int(res)
        logger.debug("Wrote {} points for user {} on assignment {}"
                     .format(points, user.pk, assignment_id))
    logger.debug("{}/{} successes".format(success, total))
    response['success'], response['total'] = success, total
    return response
