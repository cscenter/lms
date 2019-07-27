from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.registry import role_registry


class Roles(DjangoChoices):
    PROJECT_REVIEWER = C(9, _('Project reviewer'), permissions=(
        "learning.view_projects_menu",
    ))
    CURATOR_PROJECTS = C(10, _('Curator of projects'), permissions=(
        "learning.view_projects_menu",
    ))


role_registry.register(Roles.PROJECT_REVIEWER,
                       Roles.get_choice(Roles.PROJECT_REVIEWER).permissions)
role_registry.register(Roles.CURATOR_PROJECTS,
                       Roles.get_choice(Roles.CURATOR_PROJECTS).permissions)
