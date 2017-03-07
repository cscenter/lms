from __future__ import absolute_import, unicode_literals

from django.db import models
from django.dispatch import receiver

from core.models import City
from core.context_processors import CITY_LIST


@receiver(models.signals.post_save, sender=City)
@receiver(models.signals.post_delete, sender=City)
def city_cache_clear_after_save(sender, *args, **kwargs):
    CITY_LIST["CACHE"] = []
