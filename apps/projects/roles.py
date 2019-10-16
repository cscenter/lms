from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry
from .permissions import ViewProjectsMenu, UpdateOwnReportComment, \
    UpdateReportComment


class Roles(DjangoChoices):
    PROJECT_REVIEWER = C(9, _('Project reviewer'), permissions=(
        ViewProjectsMenu,
        UpdateOwnReportComment,
    ))
    CURATOR_PROJECTS = C(10, _('Curator of projects'), permissions=(
        ViewProjectsMenu,
        UpdateReportComment,
    ))


for code, name in Roles.choices:
    role_registry.register(Role(code=code, name=name,
                                permissions=Roles.get_choice(code).permissions))
