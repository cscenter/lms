from django.utils.translation import gettext_lazy as _

from users.constants import Roles

GROUPS_IMPORT_TO_GERRIT = [
    Roles.STUDENT,
    Roles.VOLUNTEER,
    Roles.PARTNER,
    Roles.INVITED,
    Roles.TEACHER,
    Roles.GRADUATE,
    Roles.CURATOR,
]


class GerritRobotMessages:
    CHANGE_CREATED = _('Solution was submitted for code review. '
                       'Use this link to track progress: {link}.')
