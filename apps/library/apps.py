from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LibraryConfig(AppConfig):
    name = 'library'
    verbose_name = _("Library")
