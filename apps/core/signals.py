import logging

from django_ses.signals import bounce_received, complaint_received

from django.db import models
from django.dispatch import receiver

from core.models import City
from notifications.service import suspend_email_address
from users.models import User

logger = logging.getLogger()


@receiver(models.signals.post_save, sender=City)
@receiver(models.signals.post_delete, sender=City)
def city_cache_clear_after_save(sender, *args, **kwargs) -> None:
    # FIXME: cache must be shared first
    # TODO: move this signal directly to the cs club project
    # from compsciclub_ru.context_processors import BRANCHES
    # BRANCHES["CACHE"] = []
    return None


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
            # It's possible to suspend emails in `admission.Applicant`
            # model but we should check that app is installed for the current
            # configuration
            models_to_suspend = [User]
            for model_class in models_to_suspend:
                suspend_email_address(model_class, email_address, reason)


@receiver(complaint_received)
def complaint_handler(sender, mail_obj, complaint_obj, raw_message,  *args, **kwargs):
    logger.error(complaint_obj)
