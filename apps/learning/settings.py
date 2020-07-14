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
    TEN_POINT = C(2, _("10-point"), css_class="")


class GradeTypes(DjangoChoices):
    """
    Used as a grade choices for models:
        * Enrollment
        * ProjectStudent
    """
    NOT_GRADED = C('not_graded', _("Not graded"), system='__all__')
    UNSATISFACTORY = C('unsatisfactory', _("Enrollment|Unsatisfactory"),
                       system=(GradingSystems.BASE, GradingSystems.BINARY))
    CREDIT = C('pass', _("Enrollment|Pass"), system=(GradingSystems.BASE, GradingSystems.BINARY))
    GOOD = C('good', _("Good"), system=(GradingSystems.BASE,))
    EXCELLENT = C('excellent', _("Excellent"), system=(GradingSystems.BASE,))

    ONE = C('one', '1', system=(GradingSystems.TEN_POINT,))
    TWO = C('two', '2', system=(GradingSystems.TEN_POINT,))
    THREE = C('three', '3', system=(GradingSystems.TEN_POINT,))
    FOUR = C('four', '4', system=(GradingSystems.TEN_POINT,))
    FIVE = C('five', '5', system=(GradingSystems.TEN_POINT,))
    SIX = C('six', '6', system=(GradingSystems.TEN_POINT,))
    SEVEN = C('seven', '7', system=(GradingSystems.TEN_POINT,))
    EIGHT = C('eight', '8', system=(GradingSystems.TEN_POINT,))
    NINE = C('nine', '9', system=(GradingSystems.TEN_POINT,))
    TEN = C('ten', '10', system=(GradingSystems.TEN_POINT,))

    satisfactory_grades = {CREDIT.value, GOOD.value, EXCELLENT.value,
                           FIVE.value, SIX.value, SEVEN.value, EIGHT.value, NINE.value, TEN.value}

    @classmethod
    def suitable_for_grading_system(cls, choice, grading_system):
        value, _ = choice
        grade = GradeTypes.get_choice(value)
        return grade.system == '__all__' or grading_system in grade.system

    @classmethod
    def get_choices_for_grading_system(cls, grading_system):
        return list(filter(lambda c: GradeTypes.suitable_for_grading_system(c, grading_system), GradeTypes.choices))

    @classmethod
    def to_int_case_expr(cls):
        """Returns Case expression for comparing grades"""
        return Case(
            When(grade=cls.TEN, then=Value(10)),
            When(grade=cls.NINE, then=Value(9)),
            When(grade=cls.EIGHT, then=Value(8)),
            When(grade=cls.SEVEN, then=Value(7)),
            When(grade=cls.SIX, then=Value(6)),
            When(grade=cls.FIVE, then=Value(5)),
            When(grade=cls.FOUR, then=Value(4)),
            When(grade=cls.THREE, then=Value(3)),
            When(grade=cls.TWO, then=Value(2)),
            When(grade=cls.ONE, then=Value(1)),
            When(grade=cls.EXCELLENT, then=Value(4)),
            When(grade=cls.GOOD, then=Value(3)),
            When(grade=cls.CREDIT, then=Value(2)),
            When(grade=cls.UNSATISFACTORY, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
