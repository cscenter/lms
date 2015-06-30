from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class HtmlPagesConfig(AppConfig):
    name = 'htmlpages'
    verbose_name = _("Flat Pages")
