from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StatisticsConfig(AppConfig):
    name = 'stats'
    verbose_name = _("Statistics")

    def ready(self):
        pass
