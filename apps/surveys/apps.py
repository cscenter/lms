from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SurveysConfig(AppConfig):
    name = 'surveys'
    verbose_name = _("Surveys")
