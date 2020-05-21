from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

BASE_THUMBNAIL_WIDTH = 176
BASE_THUMBNAIL_HEIGHT = 246


class GenderTypes(DjangoChoices):
    MALE = C('M', _('Male'))
    FEMALE = C('F', _('Female'))
    OTHER = C('o', _('Other/Prefer Not to Say'))


class ThumbnailSizes(DjangoChoices):
    """
    Base image aspect ratio is `5:7`.
    """
    BASE = C(f'{BASE_THUMBNAIL_WIDTH}x{BASE_THUMBNAIL_HEIGHT}')
    BASE_PRINT = C('250x350')
    SQUARE = C('150x150')
    SQUARE_SMALL = C('60x60')
    # FIXME: replace?
    INTERVIEW_LIST = C('100x100')
    # On center site only
    TEACHER_LIST = C("220x308")


class Roles(DjangoChoices):
    STUDENT = C(1, _('Student'))
    TEACHER = C(2, _('Teacher'))
    GRADUATE = C(3, _('Graduate'))
    VOLUNTEER = C(4, _('Co-worker'))
    CURATOR = C(5, _('Curator'))
    INTERVIEWER = C(7, _('Interviewer [Admission]'))
    PROJECT_REVIEWER = C(9, _('Project reviewer'))
    CURATOR_PROJECTS = C(10, _('Curator of projects'))
    INVITED = C(11, _('Invited User'))


CSCENTER_ACCESS_ALLOWED = {
    Roles.STUDENT,
    Roles.VOLUNTEER,
    Roles.TEACHER,
    Roles.GRADUATE,
    Roles.INTERVIEWER,
    Roles.PROJECT_REVIEWER
}


GROUPS_IMPORT_TO_GERRIT = [
    Roles.STUDENT,
    Roles.VOLUNTEER,
    Roles.TEACHER,
    Roles.GRADUATE
]


class SHADCourseGradeTypes(DjangoChoices):
    NOT_GRADED = C('not_graded', _("Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("SHADCourseGrade|Unsatisfactory"))
    CREDIT = C('pass', _("SHADCourseGrade|Pass"))
    GOOD = C('good', _("Good"))
    EXCELLENT = C('excellent', _("Excellent"))
