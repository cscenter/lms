import abc
import logging
from abc import ABCMeta
from typing import Dict, Type

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db.transaction import atomic
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.utils.html import linebreaks, strip_tags

from notifications.base_models import EmailAddressSuspension

logger = logging.getLogger("notifications.handlers")


def suspend_email_address(obj_class: Type[EmailAddressSuspension], email: str,
                          reason: Dict[str, str]) -> None:
    if not issubclass(obj_class, EmailAddressSuspension):
        raise ValidationError(f"{obj_class} must be subclass of notifications.base_models.EmailAddressSuspension")
    obj_class.objects.filter(email=email).update(email_suspension_details=reason)


class NotificationService:
    """
    Base class which knows how to add notification to db and notify recipient
    later.
    """
    __metaclass__ = ABCMeta

    @abc.abstractmethod
    def template(self):
        pass

    @cached_property
    def _cached_template(self):
        if self.template:
            return get_template(self.template)
        return None

    @abc.abstractmethod
    def subject(self):
        pass

    def get_subject(self, notification, **kwargs):
        return self.subject

    def add_to_queue(self, *args, **kwargs):
        pass

    def __init__(self):
        self.logger = logger

    @staticmethod
    def cache_content_types():
        # FIXME: Call when cls created
        try:
            # Try to cache all content types
            from django.contrib.contenttypes.models import ContentType
            for ct in ContentType.objects.all():
                ContentType.objects._add_to_cache(ContentType.objects.db, ct)
        except AttributeError:
            pass

    @staticmethod
    def get_reply_to():
        return settings.DEFAULT_FROM_EMAIL

    @atomic
    def notify(self, notification):
        from notifications.models import Notification
        try:
            context = self.get_context(notification)
        except ObjectDoesNotExist:
            self.logger.exception("Can't get context for {}".format(
                notification.pk))
            Notification.objects.filter(pk=notification.pk).update(deleted=True)
            return
        if not notification.recipient.email:
            self.logger.warning("user {0} doesn't have an email. Mark "
                                "as deleted".format(notification.recipient))
            Notification.objects.filter(pk=notification.pk).update(deleted=True)
            return

        html_content = linebreaks(self._cached_template.render(context))
        # FIXME: Don't strip links
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(self.get_subject(notification),
                                     text_content,
                                     settings.DEFAULT_FROM_EMAIL,
                                     [notification.recipient.email],
                                     reply_to=[self.get_reply_to()])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        Notification.objects.filter(pk=notification.pk).update(emailed=True)

    def get_context(self, notification):
        return {}
