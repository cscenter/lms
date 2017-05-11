from django.apps import AppConfig
from django.db.models.signals import post_save, post_init
from django.utils.translation import ugettext_lazy as _



class LearningConfig(AppConfig):
    name = 'learning'
    verbose_name = _("Learning")

    def ready(self):
        from . import signals
