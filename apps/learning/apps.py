from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LearningConfig(AppConfig):
    name = 'learning'
    verbose_name = _("Learning")

    def ready(self):
        # Register checks
        from . import checks
        # Register app signals
        from . import signals
        # Register app permissions and roles
        from . import permissions
        from . import roles
        # Register tabs
        from . import tabs
