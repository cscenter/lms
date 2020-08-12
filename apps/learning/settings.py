# -*- coding: utf-8 -*-
import pytz
from django.conf import settings
from django.db.models import Case, When, Value, IntegerField

from django.utils.translation import gettext_lazy as _
from djchoices import DjangoChoices, C

# This setting helps calculate the last day of enrollment period if
# a custom value wasn't provided on model saving.
ENROLLMENT_DURATION = getattr(settings, 'ENROLLMENT_DURATION', 45)


class Branches(DjangoChoices):
    SPB = C("spb", _("Saint Petersburg"))
    NSK = C("nsk", _("Novosibirsk"))
    DISTANCE = C("distance", _("Branches|Distance"))


# FIXME: move to users?
class AcademicDegreeLevels(DjangoChoices):
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
    ACADEMIC_LEAVE = C('academic', _("StudentStatus|Academic leave"))
    REINSTATED = C('reinstated', _("StudentInfo|Reinstalled"))
    WILL_GRADUATE = C('will_graduate', _("StudentInfo|Will graduate"))
    GRADUATE = C('graduate', _("StudentInfo|Graduate"))

    inactive_statuses = {EXPELLED.value, ACADEMIC_LEAVE.value}

    @classmethod
    def is_inactive(cls, status):
        """
        Inactive statuses affect student permissions, e.g. expelled student
        can't enroll in a course
        """
        return status in cls.inactive_statuses


class GradingSystems(DjangoChoices):
    BASE = C(0, _("Default"), css_class="")
    BINARY = C(1, _("Binary"), css_class="__binary")


class GradeTypes(DjangoChoices):
    """
    Used as a grade choices for models:
        * Enrollment
        * ProjectStudent
    """
    NOT_GRADED = C('not_graded', _("Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("Enrollment|Unsatisfactory"))
    CREDIT = C('pass', _("Enrollment|Pass"))
    GOOD = C('good', _("Good"))
    EXCELLENT = C('excellent', _("Excellent"))

    satisfactory_grades = {CREDIT.value, GOOD.value, EXCELLENT.value}

    @classmethod
    def to_int_case_expr(cls):
        """Returns Case expression for comparing grades"""
        return Case(
            When(grade=cls.EXCELLENT, then=Value(4)),
            When(grade=cls.GOOD, then=Value(3)),
            When(grade=cls.CREDIT, then=Value(2)),
            When(grade=cls.UNSATISFACTORY, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
