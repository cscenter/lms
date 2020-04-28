from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CoursesConfig(AppConfig):
    name = 'courses'
    verbose_name = _("Courses")

    def ready(self):
        # Register app signals
        from . import signals
        # Register app permissions
        from . import permissions
        # Register tabs
        from . import tabs
