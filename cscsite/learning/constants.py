# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

GRADES = Choices(('not_graded', _("Not graded")),
                 ('unsatisfactory', _("Enrollment|Unsatisfactory")),
                 ('pass', _("Enrollment|Pass")),
                 ('good', _("Good")),
                 ('excellent', _("Excellent")))
SHORT_GRADES = Choices(('not_graded', "—"),
                       ('unsatisfactory', "н"),
                       ('pass', "з"),
                       ('good', "4"),
                       ('excellent', "5"))