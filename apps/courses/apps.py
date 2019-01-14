from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CoursesConfig(AppConfig):
    name = 'courses'
    verbose_name = _("Courses")

    def ready(self):
        # Register tabs
        from . import tabs
