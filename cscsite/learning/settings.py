# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, print_function

from django.conf import settings

# this urls will be used to redirect from '/learning/' and '/teaching/'
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

LEARNING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_student')
TEACHING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_teacher')

# Assignment types constances
ASSIGNMENT_TASK_ATTACHMENT = 0
ASSIGNMENT_COMMENT_ATTACHMENT = 1

PARTICIPANT_GROUPS = getattr(settings, 'PARTICIPANT_GROUPS', Choices(
    (1, 'STUDENT_CENTER', _('Student [CENTER]')),
    (2, 'TEACHER_CENTER', _('Teacher [CENTER]')),
    (3, 'GRADUATE_CENTER', _('Graduate')),
    (4, 'VOLUNTEER', _('Volunteer')),
    (5, 'STUDENT_CLUB', _('Student [CLUB]')),
    (6, 'TEACHER_CLUB', _('Teacher [CLUB]')),
))

STUDENT_STATUS = getattr(settings, 'STUDENT_STATUS',
                         Choices(('expelled', _("StudentInfo|Expelled")),
                                 ('reinstated', _("StudentInfo|Reinstalled")),
                                 ('will_graduate', _("StudentInfo|Will graduate"))))

GRADES = getattr(settings, 'GRADES',
                 Choices(('not_graded', _("Not graded")),
                         ('unsatisfactory', _("Enrollment|Unsatisfactory")),
                         ('pass', _("Enrollment|Pass")),
                         ('good', _("Good")),
                         ('excellent', _("Excellent"))))

SHORT_GRADES = getattr(settings, 'SHORT_GRADES',
                       Choices(('not_graded', "—"),
                               ('unsatisfactory', "н"),
                               ('pass', "з"),
                               ('good', "4"),
                               ('excellent', "5")))

SEMESTER_TYPES = getattr(settings, 'SEMESTER_TYPES',
                         Choices(('spring', _("spring")),
                                 ('summer', _("summer")),
                                 ('autumn', _("autumn"))))

FOUNDATION_YEAR = getattr(settings, 'FOUNDATION_YEAR', 2007)
# Used for semester index calculation
SEMESTER_INDEX_START = getattr(settings, 'SEMESTER_INDEX_START', 1)

SEMESTER_AUTUMN_SPRING_INDEX_DIFF = getattr(settings, 'SEMESTER_AUTUMN_SPRING_INDEX_DIFF', 1)
