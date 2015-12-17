# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

PARTICIPANT_GROUPS = Choices(
    (1, 'STUDENT_CENTER', _('Student [CENTER]')),
    (2, 'TEACHER_CENTER', _('Teacher [CENTER]')),
    (3, 'GRADUATE_CENTER', _('Graduate')),
    (4, 'VOLUNTEER', _('Volunteer')),
    (5, 'STUDENT_CLUB', _('Student [CLUB]')),
    (6, 'TEACHER_CLUB', _('Teacher [CLUB]')),
)

STUDENT_STATUS = Choices(('expelled', _("StudentInfo|Expelled")),
                         ('reinstated', _("StudentInfo|Reinstalled")),
                 ('will_graduate', _("StudentInfo|Will graduate")))

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
# Note: Save sort order!
SEMESTER_TYPES = Choices(('spring', _("spring")),
                        ('summer', _("summer")),
                        ('autumn', _("autumn")))
