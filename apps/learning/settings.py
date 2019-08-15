# -*- coding: utf-8 -*-
import pytz
from django.conf import settings

from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

ASSIGNMENT_COMMENT_ATTACHMENT = 1

# After semester starts, in days
ENROLLMENT_DURATION = getattr(settings, 'ENROLLMENT_DURATION', 45)


# FIXME: move to the core settings?
DEFAULT_BRANCH_CODE = "spb"


class Branches(DjangoChoices):
    SPB = C("spb", _("Saint Petersburg"),
            timezone=pytz.timezone('Europe/Moscow'),
            abbr=_("SPb"),
            order=1)
    NSK = C("nsk", _("Novosibirsk"),
            timezone=pytz.timezone('Asia/Novosibirsk'),
            abbr=_("Nsk"),
            order=2)
    DISTANCE = C("distance", _("Branches|Distance"),
                 timezone=pytz.timezone('Europe/Moscow'),
                 abbr=_("Distance"),
                 order=3)

    @classmethod
    def get_timezone(cls, code):
        return cls.get_choice(code).timezone if code in cls.values else None


# FIXME: move to users?
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
        * ProjectStudent
    """
    NOT_GRADED = C('not_graded', _("Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("Enrollment|Unsatisfactory"))
    CREDIT = C('pass', _("Enrollment|Pass"))
    GOOD = C('good', _("Good"))
    EXCELLENT = C('excellent', _("Excellent"))

    satisfactory_grades = {CREDIT.value, GOOD.value, EXCELLENT.value}
