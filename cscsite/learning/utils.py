import unicodecsv
import datetime
import itertools
import logging
from math import ceil

import dateutil.parser as dparser
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError, ImproperlyConfigured
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


class ImportGrades(object):

    headers = []

    def __init__(self, request, assignment):
        self.assignment = assignment
        self.request = request
        file = request.FILES['csvfile']
        self.reader = unicodecsv.DictReader(iter(file))
        self.total = 0
        self.success = 0
        self.errors = []
        if not self.headers:
            raise ImproperlyConfigured(
                "subclasses of ImportGrade must provide headers attribute")

    def process(self):
        if not self.validate_headers():
            return self.import_results()

        for row in self.reader:
            self.total += 1
            try:
                data = self.clean_data(row)
            except ValidationError as e:
                logger.debug(e.message)
                continue

            res = self.update_score(data)
            self.success += int(res)
        return self.import_results()

    def validate_headers(self):
        headers = self.reader.next()
        valid = True
        for header in self.headers:
            if header not in headers:
                valid = False
                self.errors.append(
                    "ERROR: header `{}` not found".format(header))
        return valid

    def import_results(self):
        if self.errors:
            for error_msg in self.errors:
                messages.error(self.request, error_msg)
        messages.info(self.request,
                      _("<b>Import results</b>: {}/{} successes").format(
                          self.success, self.total))
        return {'success': self.success, 'total': self.total,
                'errors': self.errors}

    def clean_data(self, row):
        raise NotImplementedError(
            'subclasses of ImportGrade must provide an clean_data() method')

    def update_score(self, data):
        raise NotImplementedError(
            'subclasses of ImportGrade must provide an update_score() method')


class ImportGradesByStepicID(ImportGrades):

    headers = ["user_id", "total"]

    def clean_data(self, row):
        stepic_id = row["user_id"].strip()
        try:
            stepic_id = int(stepic_id)
        except ValueError:
            msg = _("Can't convert user_id to int '{}'").format(stepic_id)
            logger.debug(msg)
            raise ValidationError(msg, code='invalid_user_id')
        try:
            score = int(ceil(float(row["total"])))
        except ValueError:
            msg = _("Can't convert points for user '{}'").format(stepic_id)
            logger.debug(msg)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score greater then max grade for user '{}'").format(stepic_id)
            logger.debug(msg)
            raise ValidationError(msg, code='invalid_score_value')
        return stepic_id, score

    def _get_user(self, stepic_id):
        from users.models import CSCUser
        try:
            user = CSCUser.objects.get(stepic_id=stepic_id)
            return user
        except ObjectDoesNotExist:
            msg = _("No user with stepic ID {}").format(stepic_id)
            logger.debug(msg)
        except MultipleObjectsReturned:
            msg = _("Multiple objects for user ID: {}".format(stepic_id))
            logger.error(msg)
            messages.error(self.request, msg)

    def update_score(self, data):
        stepic_id, score = data
        from learning.models import AssignmentStudent

        assignment_id = self.assignment.pk

        user = self._get_user(stepic_id)
        if not user:
            return False

        try:
            a_s = (AssignmentStudent.objects.get(assignment__pk=assignment_id,
                                                 student=user))
        except ObjectDoesNotExist:
            msg = "User ID {} with stepic ID {} doesn't have an assignment " \
                  "{}".format(user.pk, user.stepic_id, assignment_id)
            logger.debug(msg)
            return False
        a_s.grade = score
        a_s.save()
        logger.debug("Wrote {} points for user {} on assignment {}"
                     .format(score, user.pk, assignment_id))
        return True


class ImportGradesByYandexLogin(ImportGrades):

    headers = ["login", "total"]

    def clean_data(self, row):
        yandex_id = row['login'].strip()
        try:
            score = int(ceil(float(row["total"])))
        except ValueError:
            msg = _("Can't convert points for user '{}'").format(yandex_id)
            logger.debug(msg)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score greater then max grade for user '{}'").format(yandex_id)
            logger.debug(msg)
            raise ValidationError(msg, code='invalid_score_value')
        return yandex_id, score

    def _get_user(self, yandex_id):
        from users.models import CSCUser
        try:
            user = CSCUser.objects.get(yandex_id__iexact=yandex_id)
            return user
        except ObjectDoesNotExist:
            msg = _("No user with Yandex ID {}").format(yandex_id)
            logger.debug(msg)
        except MultipleObjectsReturned:
            msg = _("Multiple objects for Yandex ID: {}".format(yandex_id))
            logger.debug(msg)
            messages.error(self.request, msg)

    def update_score(self, data):
        yandex_id, score = data
        from learning.models import AssignmentStudent

        assignment_id = self.assignment.pk

        user = self._get_user(yandex_id)
        if not user:
            return False

        try:
            a_s = (AssignmentStudent.objects.get(assignment__pk=assignment_id,
                                                 student=user))
        except ObjectDoesNotExist:
            msg = "User ID {} with Yandex ID {} doesn't have an assignment " \
                  "{}".format(user.pk, user.yandex_id, assignment_id)
            logger.debug(msg)
            return False
        a_s.grade = score
        a_s.save()
        logger.debug("Wrote {} points for user {} on assignment {}"
                     .format(score, user.pk, assignment_id))
        return True


