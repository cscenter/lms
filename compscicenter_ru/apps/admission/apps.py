from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AdmissionConfig(AppConfig):
    name = 'admission'
    verbose_name = _("Admission")

    def ready(self):
        from . import signals
