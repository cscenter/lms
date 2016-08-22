from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save
from django.utils.translation import ugettext_lazy as _

from learning.projects.signals import post_save_project, pre_save_project, \
    post_save_comment


class ProjectsConfig(AppConfig):
    name = 'learning.projects'
    verbose_name = _("Student Projects")

    def ready(self):
        pre_save.connect(pre_save_project,
                         sender=self.get_model('Project'))
        post_save.connect(post_save_project,
                          sender=self.get_model('Project'))
        post_save.connect(post_save_comment,
                          sender=self.get_model('ReportComment'))
