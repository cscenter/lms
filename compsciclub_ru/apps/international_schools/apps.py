from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class Config(AppConfig):
    name = 'international_schools'
    verbose_name = _("International Schools")
