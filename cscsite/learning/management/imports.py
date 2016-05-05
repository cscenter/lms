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
        headers = self.reader.fieldnames
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
        try:
            user = user_model.objects.get(
                stepic_id=stepic_id,
                groups__in=[user_model.group_pks.STUDENT_CENTER,
                            user_model.group_pks.VOLUNTEER])
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
        assignment_id = self.assignment.pk

        user = self._get_user(stepic_id)
        if not user:
            return False

        try:
            a_s = (StudentAssignment.objects.get(assignment__pk=assignment_id,
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
        try:
            user = user_model.objects.get(
                yandex_id__iexact=yandex_id,
                groups__in=[
                    user_model.group_pks.STUDENT_CENTER,
                    user_model.group_pks.VOLUNTEER])
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
        from learning.models import StudentAssignment

        assignment_id = self.assignment.pk

        user = self._get_user(yandex_id)
        if not user:
            return False

        try:
            a_s = (StudentAssignment.objects.get(assignment__pk=assignment_id,
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