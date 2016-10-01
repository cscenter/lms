import logging
from abc import ABCMeta, abstractmethod, abstractproperty

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import linebreaks, strip_tags

logger = logging.getLogger(__name__)


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class NotificationService(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.logger = logger
        try:
            # Try to cache all content types
            from django.contrib.contenttypes.models import ContentType
            for ct in ContentType.objects.all():
                ContentType.objects._add_to_cache(ContentType.objects.db, ct)
        except AttributeError:
            pass

    def execute(self):
        """Supports notification by email only"""
        processed = 0
        for notification in self.get_notifications():
            if notification.recipient_id:
                self.notify(notification)
                processed += 1
            else:
                self.logger.warning("Recipient not found. Update your "
                                    "queryset to avoid unnecessary records")
        self.logger.info("Emails generated for config {}: {}".format(
            self.__class__, processed))

    @abstractmethod
    def get_notifications(self):
        return {}

    @abstractproperty
    def template(self):
        pass

    @abstractproperty
    def title(self):
        pass

    def get_msg_subject(self, notification):
        return self.title

    @staticmethod
    def get_email_from():
        return settings.DEFAULT_FROM_EMAIL

    def notify(self, notification):
        from notifications.models import Notification

        context = self.get_context(notification)
        if not notification.recipient.email:
            self.logger.warning("user {0} doesn't have an email".format(
                notification.recipient))
            Notification.objects.filter(pk=notification.pk).update(deleted=True)
            return

        html_content = linebreaks(render_to_string(self.template, context))
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(self.get_msg_subject(notification),
                                     text_content,
                                     self.get_email_from(),
                                     [notification.recipient.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        Notification.objects.filter(pk=notification.pk).update(emailed=True)
        self.log_record(notification)

    def log_record(self, notification):
        from django.contrib.contenttypes.models import ContentType
        ct_id = notification.target_content_type_id
        target_content_type = ContentType.objects.get_for_id(ct_id)
        ctx = {
            'id': notification.pk,
            'actor': notification.actor,
            'recipient': notification.recipient,
            'verb': notification.verb,
            'action_object_id': notification.action_object_object_id,
            'target_id': notification.target_object_id,
            'target_content_type_id': target_content_type.model
        }
        msg = '[ID %(id)s] Sender <%(actor)s> ' \
              'Recipient <%(recipient)s> ' \
              'Target: %(target_id)s [%(target_content_type_id)s]' % ctx
        self.logger.info(msg)

    @abstractmethod
    def get_context(self, notification):
        return {}

    @staticmethod
    def get_site_url(context=None):
        """Returns site url based on context information"""
        return "https://compscicenter.ru"

    def get_absolute_url(self, url, context):
        return self.get_site_url(context) + url
