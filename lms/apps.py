from importlib import import_module

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from menu import Menu


class LMSConfig(AppConfig):
    name = 'lms'
    verbose_name = _("Learning Management System")

    def ready(self):
        from django.conf import settings
        module = getattr(settings, "LMS_MENU", None)
        if module:
            # Preload menus on startup
            Menu.load_menus()
            try:
                import_module(module)
            except ModuleNotFoundError:
                raise ImproperlyConfigured("settings.LMS_MENU module not found")
