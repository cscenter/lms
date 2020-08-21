from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GalleryConfig(AppConfig):
    name = 'learning.gallery'
    verbose_name = _("Gallery")
