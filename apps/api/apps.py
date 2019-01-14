from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class APIConfig(AppConfig):
    name = 'api'
    verbose_name = _("REST API")

    def ready(self):
        pass
