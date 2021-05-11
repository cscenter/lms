from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoursesConfig(AppConfig):
    name = 'courses'
    verbose_name = _("Courses")

    def ready(self):
        # Register permissions, signals and tabs
        from . import permissions  # pylint: disable=unused-import
        from . import signals  # pylint: disable=unused-import
        from . import tabs  # pylint: disable=unused-import
