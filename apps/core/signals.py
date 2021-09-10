import logging

from django_ses.signals import bounce_received, complaint_received

from django.db import models
from django.dispatch import receiver

from compsciclub_ru.context_processors import BRANCHES
from core.models import City

logger = logging.getLogger()


@receiver(models.signals.post_save, sender=City)
@receiver(models.signals.post_delete, sender=City)
def city_cache_clear_after_save(sender, *args, **kwargs):
    BRANCHES["CACHE"] = []


@receiver(bounce_received)
def bounce_handler(sender, mail_obj, bounce_obj, raw_message, *args, **kwargs):
    message_id = mail_obj['messageId']
    recipient_list = mail_obj['destination']
    logger.error(f"Bounce received. Recipients: {recipient_list}")
    # TODO: Find all models with EmailAddressSuspension mixin and update data


@receiver(complaint_received)
def complaint_handler(sender, mail_obj, complaint_obj, raw_message,  *args, **kwargs):
    pass
