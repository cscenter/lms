from djchoices import C, DjangoChoices

from django.db.models.enums import TextChoices
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop

AUTUMN_TERM_START = '1 sep'
SPRING_TERM_START = '2 feb'  # XXX: spring term must be later than 1 jan
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
    SPECTATOR = C('spectator', _("Spectator"))
    ORGANIZER = C('organizer', _("Organizer"))


class MaterialVisibilityTypes(DjangoChoices):
    PUBLIC = C('public', _('All Users'))
    PARTICIPANTS = C('participants', _('All Students'))
    COURSE_PARTICIPANTS = C('private', _('Course Participants'))


class AssignmentFormat(DjangoChoices):
    ONLINE = C("online", _("Online Submission"))  # file or text on site
    YANDEX_CONTEST = C("ya.contest", _("Yandex.Contest"))
    EXTERNAL = C("external", _("External Service"))
    CODE_REVIEW = C("code_review", _("Code Review Submission"))
    NO_SUBMIT = C("other", _("No Submission"))  # on paper, etc

    with_checker = {CODE_REVIEW.value, YANDEX_CONTEST.value}


class AssignmentStatuses(TextChoices):
    # TODO: describe each status
    NEW = 'new', _("AssignmentStatus|New"),  # TODO: remove after integration
    NOT_SUBMITTED = 'not_submitted', _("AssignmentStatus|Not submitted"),
    ON_CHECKING = 'on_checking', _("AssignmentStatus|On checking"),
    NEED_FIXES = 'need_fixes', _("AssignmentStatus|Need fixes"),
    COMPLETED = 'completed', _("AssignmentStatus|Completed")


class AssigneeMode(TextChoices):
    DISABLED = 'off', _('Without a responsible person')
    MANUAL = 'manual', _('Choose from the list')
    STUDENT_GROUP_DEFAULT = 'sg_default', _('Student Group - Default')
    STUDENT_GROUP_CUSTOM = 'sg_custom', _('Student Group - Custom')
