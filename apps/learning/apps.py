from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LearningConfig(AppConfig):
    name = 'learning'
    verbose_name = _("Learning")

    def ready(self):
        # Register checks, signals, permissions and roles, tabs
        from . import (  # pylint: disable=unused-import
            checks, permissions, roles, signals, tabs
        )
