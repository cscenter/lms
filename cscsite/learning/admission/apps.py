from django.apps import AppConfig
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from .signals import post_save_interview_update_applicant_status, \
    post_save_interview_comment


class AdmissionConfig(AppConfig):
    name = 'learning.admission'
    verbose_name = _("Admission")

    def ready(self):
        post_save.connect(post_save_interview_update_applicant_status,
                          sender=self.get_model('Interview'))
        post_save.connect(post_save_interview_comment,
                          sender=self.get_model('Comment'))
