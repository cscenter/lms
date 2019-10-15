from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry


class Roles(DjangoChoices):
    PROJECT_REVIEWER = C(9, _('Project reviewer'), permissions=(
        "learning.view_projects_menu",
        "projects.change_own_reportcomment",
    ))
    CURATOR_PROJECTS = C(10, _('Curator of projects'), permissions=(
        "learning.view_projects_menu",
        "projects.change_reportcomment",
    ))


for code, name in Roles.choices:
    role_registry.register(Role(code=code, name=name,
                                permissions=Roles.get_choice(code).permissions))
