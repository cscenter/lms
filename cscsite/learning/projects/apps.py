from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save
from django.utils.translation import ugettext_lazy as _


class ProjectsConfig(AppConfig):
    name = 'learning.projects'
    verbose_name = _("Student Projects")
    REPORT_ATTACHMENT = 1
    REPORT_COMMENT_ATTACHMENT = 2

    def ready(self):
        from . import signals
