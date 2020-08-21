from django.utils.translation import gettext_noop, gettext_lazy as _
from djchoices import DjangoChoices, C


AUTUMN_TERM_START = '1 sep'
SPRING_TERM_START = '20 jan'  # XXX: spring term must be later than 1 jan
SUMMER_TERM_START = '1 jul'


MONDAY_WEEKDAY = 0
SUNDAY_WEEKDAY = 6
WEEKDAY_TITLES = [
    gettext_noop("Monday"),
    gettext_noop("Tuesday"),
    gettext_noop("Wednesday"),
    gettext_noop("Thursday"),
    gettext_noop("Friday"),
    gettext_noop("Saturday"),
    gettext_noop("Sunday"),
]


# FIXME: mb it needs to replace lazy translation with `gettext_noop`. Test with en version
class SemesterTypes(DjangoChoices):
    """
    Term order values must be consecutive numbers and start from
    the beginning of the year.
    """
    SPRING = C('spring', _("spring"), order=1)
    SUMMER = C('summer', _("summer"), order=2)
    AUTUMN = C('autumn', _("autumn"), order=3)


class ClassTypes(DjangoChoices):
    LECTURE = C('lecture', _("Lecture"))
    SEMINAR = C('seminar', _("Seminar"))


class TeacherRoles(DjangoChoices):
    """
    This enum is used in the CourseTeacher.roles bitfield. Order is matter!
    """
    LECTURER = C('lecturer', _("Lecturer"))
    REVIEWER = C('reviewer', _("Reviewer"))
    SEMINAR = C('seminar', _("Seminarian"))


# TODO: Make a redirect for old links and rewrite download view without this constant?
ASSIGNMENT_TASK_ATTACHMENT = 0


class MaterialVisibilityTypes(DjangoChoices):
    VISIBLE = C('all', _('All Users'))
    HIDDEN = C('students', _('Only Students'))
