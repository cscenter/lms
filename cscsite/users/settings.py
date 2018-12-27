from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

PROFILE_THUMBNAIL_WIDTH = 170
PROFILE_THUMBNAIL_HEIGHT = 238


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


GROUPS_IMPORT_TO_GERRIT = [
    AcademicRoles.STUDENT_CENTER,
    AcademicRoles.VOLUNTEER,
    AcademicRoles.TEACHER_CENTER,
    AcademicRoles.GRADUATE_CENTER
]
