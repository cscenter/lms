from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApplicationConfig(AppConfig):
    name = 'application'
    verbose_name = _("Application")

    def ready(self):
        pass
