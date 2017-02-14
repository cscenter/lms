from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AdmissionConfig(AppConfig):
    name = 'learning.admission'
    verbose_name = _("Admission")

    def ready(self):
        from .signals import (post_save_interview, post_save_interview_comment)
