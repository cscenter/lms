from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProjectsConfig(AppConfig):
    name = 'learning.projects'
    verbose_name = _("Student Projects")
    REPORT_ATTACHMENT = 1
    REPORT_COMMENT_ATTACHMENT = 2

    def ready(self):
        # Register app permissions and roles
        from . import permissions
        from . import roles
        # Register signals
        from . import signals
