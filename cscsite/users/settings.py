from django.conf import settings

from learning.settings import AcademicRoles

PROFILE_THUMBNAIL_WIDTH = getattr(settings, 'PROFILE_THUMBNAIL_WIDTH',  170)
PROFILE_THUMBNAIL_HEIGHT = getattr(settings, 'PROFILE_THUMBNAIL_HEIGHT',  238)

GROUPS_IMPORT_TO_GERRIT = [
    AcademicRoles.STUDENT_CENTER,
    AcademicRoles.VOLUNTEER,
    AcademicRoles.TEACHER_CENTER,
    AcademicRoles.GRADUATE_CENTER
]
