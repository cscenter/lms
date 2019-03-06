from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AdmissionConfig(AppConfig):
    name = 'admission'
    verbose_name = _("Admission")
    INVITATION_EXPIRED_IN_HOURS = 27

    def ready(self):
        from . import signals
