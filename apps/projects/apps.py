from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    name = 'projects'
    verbose_name = _("Student Projects")

    def ready(self):
        # Register app permissions, roles and signals
        from . import permissions, roles, signals  # pylint: disable=unused-import
