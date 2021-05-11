from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CodeReviewsConfig(AppConfig):
    name = 'code_reviews'
    verbose_name = _("Code Review")

    def ready(self):
        from . import signals  # pylint: disable=unused-import
