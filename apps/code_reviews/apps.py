from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class CodeReviewsConfig(AppConfig):
    name = 'code_reviews'
    verbose_name = _("Code Review")

    def ready(self):
        from . import roles  # pylint: disable=unused-import
        is_gerrit_password_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
        if is_gerrit_password_sync_enabled:
            from .gerrit import signals  # pylint: disable=unused-import
