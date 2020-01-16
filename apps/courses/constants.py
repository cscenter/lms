from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C


AUTUMN_TERM_START = '1 sep'
SPRING_TERM_START = '20 jan'  # XXX: spring term must be later than 1 jan
SUMMER_TERM_START = '1 jul'


MONDAY_WEEKDAY = 0


class SemesterTypes(DjangoChoices):
    """
    For ordering use the first term in a year as starting point.
    Term order values must be consecutive numbers.
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
