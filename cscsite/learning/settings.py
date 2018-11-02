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


class AcademicRoles(DjangoChoices):
    STUDENT_CENTER = C(1, _('Student [CENTER]'))
    TEACHER_CENTER = C(2, _('Teacher [CENTER]'))
    GRADUATE_CENTER = C(3, _('Graduate'))
    VOLUNTEER = C(4, _('Volunteer'))
    STUDENT_CLUB = C(5, _('Student [CLUB]'))
    TEACHER_CLUB = C(6, _('Teacher [CLUB]'))
    INTERVIEWER = C(7, _('Interviewer [Admission]'))
    MASTERS_DEGREE = C(8, _('Studying for a master degree'))
    PROJECT_REVIEWER = C(9, _('Project reviewer'))
    CURATOR_PROJECTS = C(10, _('Curator of projects'))


GROUPS_HAS_ACCESS_TO_CENTER = (
    AcademicRoles.STUDENT_CENTER,
    AcademicRoles.VOLUNTEER,
    AcademicRoles.TEACHER_CENTER,
    AcademicRoles.GRADUATE_CENTER,
    AcademicRoles.INTERVIEWER,
    # MASTERS_DEGREE should be always set with one of the student group
    AcademicRoles.PROJECT_REVIEWER,
)

STUDENT_STATUS = getattr(settings, 'STUDENT_STATUS',
                         Choices(('expelled', _("StudentInfo|Expelled")),
                                 ('reinstated', _("StudentInfo|Reinstalled")),
                                 ('will_graduate', _("StudentInfo|Will graduate"))))


class GradingTypes(DjangoChoices):
    default = C(0, _("Default"), css_class="")
    binary = C(1, _("Binary"), css_class="__binary")


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


class SemesterTypes(DjangoChoices):
    spring = C('spring', _("spring"))
    summer = C('summer', _("summer"))
    autumn = C('autumn', _("autumn"))


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


class AcademicDegreeYears(DjangoChoices):
    BACHELOR_SPECIALITY_1 = C("1", _('1 course bachelor, speciality'))
    BACHELOR_SPECIALITY_2 = C("2", _('2 course bachelor, speciality'))
    BACHELOR_SPECIALITY_3 = C("3", _('3 course bachelor, speciality'))
    BACHELOR_SPECIALITY_4 = C("4", _('4 course bachelor, speciality'))
    SPECIALITY_5 = C("5", _('last course speciality'))
    MASTER_1 = C("6", _('1 course magistracy'))
    MASTER_2 = C("7", _('2 course magistracy'))
    POSTGRADUATE = C("8", _('postgraduate'))
    GRADUATE = C("9", _('graduate'))


TERMS_IN_ACADEMIC_YEAR = len(SemesterTypes.choices)

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
