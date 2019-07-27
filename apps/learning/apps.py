from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class LearningConfig(AppConfig):
    name = 'learning'
    verbose_name = _("Learning")

    def ready(self):
        from . import signals
        # Register app permissions and roles
        from . import permissions
        from . import roles
        # Register tabs
        from . import tabs
