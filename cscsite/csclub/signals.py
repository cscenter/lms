from __future__ import absolute_import, unicode_literals

from django.db import models
from django.dispatch import receiver

from core.models import City
from csclub.context_processors import CITIES_LIST
print 'import'

@receiver(models.signals.post_save, sender=City)
def city_cache_clear_after_save(sender, created, instance, **kwargs):
    del CITIES_LIST[:]
    print 'WTF'
