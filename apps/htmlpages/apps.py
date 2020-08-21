from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HtmlPagesConfig(AppConfig):
    name = 'htmlpages'
    verbose_name = _("Flat Pages")
