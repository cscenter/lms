from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PublicationsConfig(AppConfig):
    name = 'publications'
    verbose_name = _("Publications")
