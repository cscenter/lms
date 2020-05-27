from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class UsefulConfig(AppConfig):
    name = 'useful'
    verbose_name = _("Useful")
