# -*- coding: utf-8 -*-

from django.conf import settings

from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

# this urls will be used to redirect from '/learning/' and '/teaching/'
LEARNING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_student')
TEACHING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_teacher')

# TODO: try to replace with builtin `formats.date_format`
DATE_FORMAT_RU = "%d.%m.%Y"
TIME_FORMAT_RU = "%H:%M"

# Assignment types constants
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
    # Should be always set with one of the student group
    MASTERS_DEGREE = C(8, _('Studying for a master degree'))
    PROJECT_REVIEWER = C(9, _('Project reviewer'))
    CURATOR_PROJECTS = C(10, _('Curator of projects'))

    has_access_to_cscenter = {
        STUDENT_CENTER.value,
        VOLUNTEER.value,
        TEACHER_CENTER.value,
        GRADUATE_CENTER.value,
        INTERVIEWER.value,
        PROJECT_REVIEWER.value
    }


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


class StudentStatuses(DjangoChoices):
    EXPELLED = C('expelled', _("StudentInfo|Expelled"))
    REINSTATED = C('reinstated', _("StudentInfo|Reinstalled"))
    WILL_GRADUATE = C('will_graduate', _("StudentInfo|Will graduate"))


class GradingSystems(DjangoChoices):
    BASE = C(0, _("Default"), css_class="")
    BINARY = C(1, _("Binary"), css_class="__binary")


class GradeTypes(DjangoChoices):
    """
    Used as a grade choices for models:
        * Enrollment
        * SHADCourseRecord
        * ProjectStudent
    """
    NOT_GRADED = C('not_graded', _("Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("Enrollment|Unsatisfactory"))
    CREDIT = C('pass', _("Enrollment|Pass"))
    GOOD = C('good', _("Good"))
    EXCELLENT = C('excellent', _("Excellent"))

    satisfactory_grades = {CREDIT.value, GOOD.value, EXCELLENT.value}


# FIXME: AssignmentStates точно деталь реализации (перенести или забить уже?), которая не шарится с другими приложениями, что насчет semestertypes и classtypes?
class AssignmentStates(DjangoChoices):
    NOT_SUBMITTED = C("not_submitted", _("Assignment|not submitted"),
                      abbr="—", css_class="not-submitted")
    NOT_CHECKED = C("not_checked", _("Assignment|not checked"),
                    abbr="…", css_class="not-checked")
    UNSATISFACTORY = C("unsatisfactory", _("Assignment|unsatisfactory"),
                       abbr="2", css_class="unsatisfactory")
    CREDIT = C("pass", _("Assignment|pass"),
               abbr="3", css_class="pass")
    GOOD = C("good", _("Assignment|good"),
             abbr="4", css_class="good")
    EXCELLENT = C("excellent", _("Assignment|excellent"),
                  abbr="5", css_class="excellent")


# TODO: Добавить в модель Semester, использовать как дефолтные значения при создании семестра
AUTUMN_TERM_START = '1 sep'
SPRING_TERM_START = '20 jan'  # XXX: spring term must be later than 1 jan
SUMMER_TERM_START = '1 jul'

# FIXME: а вот это точно можно в настройки семестра вынести
ENROLLMENT_DURATION = getattr(settings, 'ENROLLMENT_DURATION', 45)  # after semester starts, in days

# Presume foundation year starts from spring term
FOUNDATION_YEAR = getattr(settings, 'FOUNDATION_YEAR', 2007)
CENTER_FOUNDATION_YEAR = getattr(settings, 'CENTER_FOUNDATION_YEAR', 2011)
