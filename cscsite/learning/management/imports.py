# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function
import logging
import unicodecsv
from math import ceil

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, \
    ValidationError, ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from learning.models import StudentAssignment

logger = logging.getLogger(__name__)
user_model = get_user_model()

# TODO: Create management command. mock request?


class ImportGrades(object):
    headers = None

    def __init__(self, request, assignment):
        self.assignment = assignment
        self.request = request
        file = request.FILES['csv_file']
        self.reader = unicodecsv.DictReader(iter(file))
        self.total = 0
        self.success = 0
        self.errors = []
        if not self.headers:
            raise ImproperlyConfigured(
                "subclasses of ImportGrade must provide headers attribute")

    def import_data(self):
        if not self.headers_are_valid():
            messages.error(self.request, "<br>".join(self.errors))
            return self.import_results()

        for row in self.reader:
            self.total += 1
            try:
                data = self.clean_data(row)
                res = self.update_score(data)
                self.success += int(res)
            except ValidationError as e:
                logger.debug(e.message)
        return self.import_results()

    def headers_are_valid(self):
        headers = self.reader.fieldnames
        valid = True
        for header in self.headers:
            if header not in headers:
                valid = False
                self.errors.append(
                    "ERROR: header `{}` not found".format(header))
        return valid

    def import_results(self):
        messages.info(self.request,
                      _("<b>Import results</b>: {}/{} successes").format(
                          self.success, self.total))
        return {'success': self.success, 'total': self.total,
                'errors': self.errors}

    def clean_data(self, row):
        raise NotImplementedError(
            'subclasses of ImportGrade must provide clean_data() method')

    def update_score(self, data):
        raise NotImplementedError(
            'subclasses of ImportGrade must provide update_score() method')


class ImportGradesByStepicID(ImportGrades):
    headers = ["user_id", "total"]

    def clean_data(self, row):
        stepic_id = row["user_id"].strip()
        try:
            stepic_id = int(stepic_id)
        except ValueError:
            msg = _("Can't convert user_id to int '{}'").format(stepic_id)
            raise ValidationError(msg, code='invalid_user_id')
        try:
            score = int(ceil(float(row["total"])))
        except ValueError:
            msg = _("Can't convert points for user '{}'").format(stepic_id)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score greater than max value for id '{}'").format(stepic_id)
            raise ValidationError(msg, code='invalid_score_value')
        return stepic_id, score

    def update_score(self, data):
        stepic_id, score = data
        assignment_id = self.assignment.pk

        user_id = self._get_user_id(stepic_id)
        if not user_id:
            return False

        updated = (StudentAssignment.objects
                   .filter(assignment__id=assignment_id,
                           student_id=user_id)
                   .update(grade=score))
        if not updated:
            msg = "User with id={} and stepic_id={} doesn't have " \
                  "an assignment {}".format(user_id, stepic_id, assignment_id)
            logger.debug(msg)
            return False
        logger.debug("Has written {} points for user_id={} on assignment_id={}"
                     .format(score, user_id, assignment_id))
        return True

    def _get_user_id(self, stepic_id):
        ids = (user_model.objects
               .filter(
                    stepic_id=stepic_id,
                    groups__in=[user_model.group.STUDENT_CENTER,
                                user_model.group.VOLUNTEER])
               .values_list('id', flat=True)
               .order_by())
        if len(ids) == 0:
            msg = _("User with stepic_id {} not found").format(stepic_id)
            logger.debug(msg)
        elif len(ids) > 1:
            msg = _("Multiple objects for stepic_id {}".format(stepic_id))
            logger.error(msg)
            messages.error(self.request, msg)
        else:
            return ids[0]


class ImportGradesByYandexLogin(ImportGrades):
    headers = ["login", "total"]

    def clean_data(self, row):
        yandex_id = row['login'].strip()
        try:
            score = int(ceil(float(row["total"])))
        except ValueError:
            msg = _("Can't convert points for user '{}'").format(yandex_id)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score greater then max grade for user '{}'").format(yandex_id)
            raise ValidationError(msg, code='invalid_score_value')
        return yandex_id, score

    def update_score(self, data):
        yandex_id, score = data
        from learning.models import StudentAssignment

        assignment_id = self.assignment.pk

        user_id = self._get_user_id(yandex_id)
        if not user_id:
            return False

        updated = (StudentAssignment.objects
                   .filter(assignment__id=assignment_id,
                           student_id=user_id)
                   .update(grade=score))
        if not updated:
            msg = "User with id={} and yandex_id={} doesn't have " \
                  "an assignment".format(user_id, yandex_id)
            logger.debug(msg)
            return False
        logger.debug("Has written {} points for user_id={} on assignment_id={}"
                     .format(score, user_id, assignment_id))
        return True

    def _get_user_id(self, yandex_id):
        ids = (user_model.objects
               .filter(
                    yandex_id__iexact=yandex_id,
                    groups__in=[user_model.group.STUDENT_CENTER,
                                user_model.group.VOLUNTEER])
               .values_list('id', flat=True)
               .order_by())
        if len(ids) == 0:
            msg = _("User with yandex_id {} not found").format(yandex_id)
            logger.debug(msg)
        elif len(ids) > 1:
            msg = _("Multiple objects for yandex_id {}".format(yandex_id))
            logger.error(msg)
            messages.error(self.request, msg)
        else:
            return ids[0]
