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


class AcademicRoles(DjangoChoices):
    STUDENT = C(1, _('Student [CENTER]'))
    TEACHER_CENTER = C(2, _('Teacher [CENTER]'))
    GRADUATE_CENTER = C(3, _('Graduate'))
    VOLUNTEER = C(4, _('Volunteer'))
    STUDENT_CLUB = C(5, _('Student [CLUB]'))
    TEACHER_CLUB = C(6, _('Teacher [CLUB]'))
    INTERVIEWER = C(7, _('Interviewer [Admission]'))
    # Should be always set with one of the student group
    # FIXME: Rename it
    MASTERS_DEGREE = C(8, _('Studying for a master degree'))
    PROJECT_REVIEWER = C(9, _('Project reviewer'))
    CURATOR_PROJECTS = C(10, _('Curator of projects'))


CSCENTER_ACCESS_ALLOWED = {
    AcademicRoles.STUDENT,
    AcademicRoles.VOLUNTEER,
    AcademicRoles.TEACHER_CENTER,
    AcademicRoles.GRADUATE_CENTER,
    AcademicRoles.INTERVIEWER,
    AcademicRoles.PROJECT_REVIEWER
}


GROUPS_IMPORT_TO_GERRIT = [
    AcademicRoles.STUDENT,
    AcademicRoles.VOLUNTEER,
    AcademicRoles.TEACHER_CENTER,
    AcademicRoles.GRADUATE_CENTER
]


class SHADCourseGradeTypes(DjangoChoices):
    NOT_GRADED = C('not_graded', _("Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("SHADCourseGrade|Unsatisfactory"))
    CREDIT = C('pass', _("SHADCourseGrade|Pass"))
    GOOD = C('good', _("Good"))
    EXCELLENT = C('excellent', _("Excellent"))
