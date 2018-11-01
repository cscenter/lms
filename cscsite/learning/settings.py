# -*- coding: utf-8 -*-

from django.conf import settings

# this urls will be used to redirect from '/learning/' and '/teaching/'
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C
from model_utils import Choices

LEARNING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_student')
TEACHING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_teacher')

# TODO: try to replace with builtin `formats.date_format`
DATE_FORMAT_RU = "%d.%m.%Y"
TIME_FORMAT_RU = "%H:%M"

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
    (7, 'INTERVIEWER', _('Interviewer [Admission]')),
    (8, 'MASTERS_DEGREE', _('Studying for a master degree')),
    (9, 'PROJECT_REVIEWER', _('Project reviewer')),
    (10, 'CURATOR_PROJECTS', _('Curator of projects')),
))

GROUPS_HAS_ACCESS_TO_CENTER = (
    PARTICIPANT_GROUPS.STUDENT_CENTER,
    PARTICIPANT_GROUPS.VOLUNTEER,
    PARTICIPANT_GROUPS.TEACHER_CENTER,
    PARTICIPANT_GROUPS.GRADUATE_CENTER,
    PARTICIPANT_GROUPS.INTERVIEWER,
    # MASTERS_DEGREE should be always set with one of the student group
    PARTICIPANT_GROUPS.PROJECT_REVIEWER,
)

STUDENT_STATUS = getattr(settings, 'STUDENT_STATUS',
                         Choices(('expelled', _("StudentInfo|Expelled")),
                                 ('reinstated', _("StudentInfo|Reinstalled")),
                                 ('will_graduate', _("StudentInfo|Will graduate"))))

GRADING_TYPES = getattr(settings, 'GRADE_TYPES',
    Choices((0, 'default', _("Default")),  # 4 state, if graded
            (1, 'binary', _("Binary"))))  # (un)satisfy, if graded

GRADES = getattr(settings, 'GRADES',
                 Choices(('not_graded', 'not_graded', _("Not graded")),
                         ('unsatisfactory', 'unsatisfactory', _("Enrollment|Unsatisfactory")),
                         ('pass', 'credit', _("Enrollment|Pass")),
                         ('good', 'good', _("Good")),
                         ('excellent', 'excellent', _("Excellent"))))

POSITIVE_GRADES = {
    GRADES.credit,
    GRADES.good,
    GRADES.excellent,
}

SHORT_GRADES = getattr(settings, 'SHORT_GRADES',
                       Choices(('not_graded', 'not_graded', "—"),
                               ('unsatisfactory', 'unsatisfactory', "н"),
                               ('pass', 'pass', "з"),
                               ('good', 'good', "4"),
                               ('excellent', 'excellent', "5")))

SEMESTER_TYPES = getattr(settings, 'SEMESTER_TYPES',
                         Choices(('spring', _("spring")),
                                 ('summer', _("summer")),
                                 ('autumn', _("autumn"))))


class AssignmentStates(DjangoChoices):
    not_submitted = C("not_submitted", _("Assignment|not submitted"),
                      abbr="—", css_class="not-submitted")
    not_checked = C("not_checked", _("Assignment|not checked"),
                    abbr="…", css_class="not-checked")
    unsatisfactory = C("unsatisfactory", _("Assignment|unsatisfactory"),
                       abbr="2", css_class="unsatisfactory")
    credit = C("pass", _("Assignment|pass"),
               abbr="3", css_class="pass")
    good = C("good", _("Assignment|good"),
             abbr="4", css_class="good")
    excellent = C("excellent", _("Assignment|excellent"),
                  abbr="5", css_class="excellent")


TERMS_IN_ACADEMIC_YEAR = len(SEMESTER_TYPES)

# don't know what will happen if we change this when there are models in DB
AUTUMN_TERM_START = '1 sep'
# XXX: spring semester must be later than 1 jan
SPRING_TERM_START = '20 jan'
SUMMER_TERM_START = '1 jul'

ENROLLMENT_DURATION = getattr(settings, 'ENROLLMENT_DURATION', 45)  # after semester starts, in days

# Presume foundation year starts from spring term
FOUNDATION_YEAR = getattr(settings, 'FOUNDATION_YEAR', 2007)
CENTER_FOUNDATION_YEAR = getattr(settings, 'CENTER_FOUNDATION_YEAR', 2011)
# Used for semester index calculation
TERMS_INDEX_START = getattr(settings, 'TERMS_INDEX_START', 1)

SEMESTER_AUTUMN_SPRING_INDEX_OFFSET = getattr(settings,
                                            'SEMESTER_AUTUMN_SPRING_INDEX_DIFF',
                                              1)

PROFILE_THUMBNAIL_WIDTH = getattr(settings, 'PROFILE_THUMBNAIL_WIDTH',  170)
PROFILE_THUMBNAIL_HEIGHT = getattr(settings, 'PROFILE_THUMBNAIL_HEIGHT',  238)
