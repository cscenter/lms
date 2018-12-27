from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class InternshipsConfig(AppConfig):
    name = 'learning.internships'
    verbose_name = _("Internships")
