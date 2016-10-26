from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save
from django.utils.translation import ugettext_lazy as _


class ProjectsConfig(AppConfig):
    name = 'learning.projects'
    verbose_name = _("Student Projects")
    REPORT_ATTACHMENT = 1
    REPORT_COMMENT_ATTACHMENT = 2

    def ready(self):
        from learning.projects import signals
        from learning.projects.signals import post_save_project_student
        pre_save.connect(signals.pre_save_project,
                         sender=self.get_model('Project'))
        post_save.connect(signals.post_save_project,
                          sender=self.get_model('Project'))
        post_save.connect(signals.post_save_report,
                          sender=self.get_model('Report'))
        post_save.connect(signals.post_save_review,
                          sender=self.get_model('Review'))
        post_save.connect(signals.post_save_comment,
                          sender=self.get_model('ReportComment'))
