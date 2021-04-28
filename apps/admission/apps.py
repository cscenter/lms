from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdmissionConfig(AppConfig):
    name = 'admission'
    verbose_name = _("Admission")

    def ready(self):
        # Register app permissions, roles and signals
        from . import permissions, roles, signals  # pylint: disable=unused-import
