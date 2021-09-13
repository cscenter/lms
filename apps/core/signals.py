import logging

from django_ses.signals import bounce_received, complaint_received

from django.db import models
from django.dispatch import receiver

from admission.models import Applicant
from compsciclub_ru.context_processors import BRANCHES
from core.models import City
from notifications.service import suspend_email_address
from users.models import User

logger = logging.getLogger()


@receiver(models.signals.post_save, sender=City)
@receiver(models.signals.post_delete, sender=City)
def city_cache_clear_after_save(sender, *args, **kwargs) -> None:
    return None  # FIXME: cache must be shared first
    BRANCHES["CACHE"] = []


@receiver(bounce_received)
def bounce_handler(sender, mail_obj, bounce_obj, *args, **kwargs):
    if bounce_obj['bounceType'] == 'Permanent':
        for bounced_recipient in bounce_obj['bouncedRecipients']:
            email_address = bounced_recipient.pop('emailAddress')
            reason = {
                'timestamp': bounce_obj['timestamp'],
                'bounceSubType': bounce_obj['bounceSubType'],
                **bounced_recipient
            }
            models_to_suspend = [User, Applicant]
            for model_class in models_to_suspend:
                suspend_email_address(model_class, email_address, reason)


@receiver(complaint_received)
def complaint_handler(sender, mail_obj, complaint_obj, raw_message,  *args, **kwargs):
    pass
