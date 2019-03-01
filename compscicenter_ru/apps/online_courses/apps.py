from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class Config(AppConfig):
    name = 'online_courses'
    verbose_name = _("Online courses")
