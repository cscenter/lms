from enum import Enum, unique

from django.core.exceptions import ValidationError
from djchoices import C, DjangoChoices, ChoiceItem

from django.conf import settings
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

# This setting helps calculate the last day of enrollment period if
# a custom value wasn't provided on model saving.
ENROLLMENT_DURATION = getattr(settings, 'ENROLLMENT_DURATION', 45)


# TODO: remove
class Branches(DjangoChoices):
    SPB = C("spb", _("Saint Petersburg"))
    NSK = C("nsk", _("Novosibirsk"))
    DISTANCE = C("distance", _("Branches|Distance"))
    DISTANCE_2019 = C("distance_2019", _("Branches|Distance"))


# FIXME: move to users?
class AcademicDegreeLevels(DjangoChoices):
    BACHELOR_SPECIALITY_1 = C("1", _('1 course bachelor, speciality'))
    BACHELOR_SPECIALITY_2 = C("2", _('2 course bachelor, speciality'))
    BACHELOR_SPECIALITY_3 = C("3", _('3 course bachelor, speciality'))
    BACHELOR_SPECIALITY_4 = C("4", _('4 course bachelor, speciality'))
    SPECIALITY_5 = C("5", _('5 course speciality'))
    SPECIALITY_6 = C("6", _('6 course speciality'))
    MASTER_1 = C("7", _('1 course magistracy'))
    MASTER_2 = C("8", _('2 course magistracy'))
    POSTGRADUATE = C("9", _('postgraduate'))
    ACADEMIC_LEAVE = C("10", _('academic_leave'))
    OTHER = C("other", _('Other'))

class InvitationCategories(DjangoChoices):
    UNIVERSITY = C("university", _("Invitation|University"))
    STAFF = C("staff", _("Invitation|Staff"))
    TEACHER = C("teacher", _("Invitation|Teacher"))
    GUEST = C("guest", _("Invitation|Guest"))
    ACADEMIC = C("academic", _("Invitation|Aacdemic"))
    GRADUATE = C("graduate", _("Invitation|Graduate"))
    APPLICANT = C("applicant", _("Invitation|Applicant"))

class StudentStatuses(DjangoChoices):
    EXPELLED = C('expelled', _("StudentInfo|Expelled"))
    ACADEMIC_LEAVE = C('academic', _("StudentStatus|Academic leave"))
    ACADEMIC_LEAVE_SECOND = C('academic_2', _("Second academic leave"))
    REINSTATED = C('reinstated', _("StudentInfo|Reinstalled"))
    WILL_GRADUATE = C('will_graduate', _("StudentInfo|Will graduate"))
    GRADUATE = C('graduate', _("StudentInfo|Graduate"))

    inactive_statuses = {EXPELLED.value, ACADEMIC_LEAVE.value, ACADEMIC_LEAVE_SECOND.value}

    @classmethod
    def is_inactive(cls, status):
        """
        Inactive statuses affect student permissions, e.g. expelled student
        can't enroll in a course
        """
        return status in cls.inactive_statuses


class GradingSystems(DjangoChoices):
    BASE = C(0, _("Default"), css_class="")
    BINARY = C(1, _("Pass/Fail"), css_class="__binary")
    BINARY_PLUS_EXCELLENT = C(3, _("Pass/Fail + Excellent"), css_class="")
    TEN_POINT = C(2, _("10-point scale"), css_class="")


class GradeTypes(DjangoChoices):
    """
    Used as grade choices for the Enrollment model and as default_grade choices for Course model.
    """
    NOT_GRADED = C('not_graded', _("Not graded"), system='__all__',
                   russian_label="Без оценки", order=0)
    WITHOUT_GRADE = C('without_grade', _("Without Grade"), system='__all__',
                   russian_label="Курс без оценки", order=0)
    UNSATISFACTORY = C('unsatisfactory', _("Enrollment|Unsatisfactory"), system=(
        GradingSystems.BASE, GradingSystems.BINARY, GradingSystems.BINARY_PLUS_EXCELLENT
    ), russian_label="Незачет", order=11)
    CREDIT = C('pass', _("Enrollment|Pass"), system=(
        GradingSystems.BASE, GradingSystems.BINARY, GradingSystems.BINARY_PLUS_EXCELLENT
    ), russian_label="Зачет", order=12)
    GOOD = C('good', _("Good"), system=(GradingSystems.BASE,), russian_label="Хорошо", order=13)
    EXCELLENT = C('excellent', _("Excellent"), system=(
        GradingSystems.BASE, GradingSystems.BINARY_PLUS_EXCELLENT
    ), russian_label="Отлично", order=14)
    RE_CREDIT = C('re-credit', _("Enrollment|Re-credit"), system='__all__',
                  russian_label="Перезачтено", order=15)

    ONE = C('one', '1', system=(GradingSystems.TEN_POINT,),
            russian_label="1", order=1)
    TWO = C('two', '2', system=(GradingSystems.TEN_POINT,),
            russian_label="2", order=2)
    THREE = C('three', '3', system=(GradingSystems.TEN_POINT,),
              russian_label="3", order=3)
    FOUR = C('four', '4', system=(GradingSystems.TEN_POINT,),
             russian_label="4", order=4)
    FIVE = C('five', '5', system=(GradingSystems.TEN_POINT,),
             russian_label="5", order=5)
    SIX = C('six', '6', system=(GradingSystems.TEN_POINT,),
            russian_label="6", order=6)
    SEVEN = C('seven', '7', system=(GradingSystems.TEN_POINT,),
              russian_label="7", order=7)
    EIGHT = C('eight', '8', system=(GradingSystems.TEN_POINT,),
              russian_label="8", order=8)
    NINE = C('nine', '9', system=(GradingSystems.TEN_POINT,),
             russian_label="9", order=9)
    TEN = C('ten', '10', system=(GradingSystems.TEN_POINT,),
            russian_label="10", order=10)

    excellent_grades = {EXCELLENT.value, NINE.value, TEN.value}
    good_grades = {GOOD.value, SEVEN.value, EIGHT.value}
    satisfactory_grades = {CREDIT.value, RE_CREDIT.value, GOOD.value, EXCELLENT.value,
                           FOUR.value, FIVE.value, SIX.value, SEVEN.value, EIGHT.value, NINE.value, TEN.value}
    unsatisfactory_grades = {NOT_GRADED.value, UNSATISFACTORY.value, WITHOUT_GRADE.value,
                             ONE.value, TWO.value, THREE.value}
    default_grades = {
        (NOT_GRADED.value, NOT_GRADED.label),
        (WITHOUT_GRADE.value, WITHOUT_GRADE.label),
    }

    @classmethod
    def is_suitable_for_grading_system(cls, choice, grading_system):
        value, _ = choice
        grade = GradeTypes.get_choice(value)
        return grade.system == '__all__' or grading_system in grade.system

    @classmethod
    def get_choices_for_grading_system(cls, grading_system):
        return list(filter(lambda c: GradeTypes.is_suitable_for_grading_system(c, grading_system), GradeTypes.choices))

    @classmethod
    def get_grades_for_grading_system(cls, grading_system):
        return [grade[0] for grade in cls.get_choices_for_grading_system(grading_system)]

    @classmethod
    def get_choice_from_russian_label(cls, russian_label: str) -> ChoiceItem:
        label = (russian_label.lower()
                 .replace('ё', 'е').capitalize())
        for db_value, _ in cls.choices:
            choice = cls.get_choice(db_value)
            if choice.russian_label == label:
                return choice
        raise ValidationError(f"Оценки '{russian_label}' не существует.")


class EnrollmentGradeUpdateSource(TextChoices):
    GRADEBOOK = 'gradebook', _("Gradebook")
    CSV_YANDEX_LOGIN = 'csv-ya.login', _("Imported from CSV by Yandex.Login")
    CSV_STEPIK = 'csv-stepik', _("Imported from CSV by stepik.org ID")
    CSV_ENROLLMENT = 'csv-enrollment', _("Imported from CSV by LMS Student ID")
    FORM_ADMIN = 'admin', _("Admin Panel")


class AssignmentScoreUpdateSource(TextChoices):
    API = 'api', _("REST API")
    API_YANDEX_CONTEST = 'api-ya.contest', _("Yandex.Contest")
    CSV_YANDEX_LOGIN = 'csv-ya.login', _("Imported from CSV by Yandex.Login")
    CSV_STEPIK = 'csv-stepik', _("Imported from CSV by stepik.org ID")
    CSV_ENROLLMENT = 'csv-enrollment', _("Imported from CSV by LMS Student ID")
    FORM_ADMIN = 'admin', _("Admin Panel")
    FORM_ASSIGNMENT = 'form', _("Form on Assignment Detail Page")
    FORM_GRADEBOOK = 'gradebook', _("Gradebook")
    WEBHOOK_GERRIT = 'webhook-gerrit', _("Gerrit Webhook")
