import abc
import logging
from abc import ABCMeta, abstractmethod, abstractproperty

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db.models import Model
from django.db.transaction import atomic
from django.template.loader import render_to_string, get_template
from django.utils.functional import cached_property
from django.utils.html import linebreaks, strip_tags

from users.constants import AcademicRoles

logger = logging.getLogger("notifications.handlers")


class NotificationService:
    """
    Base class which knows how to add notification to db and notify recipient
    later.
    """
    __metaclass__ = ABCMeta

    SITE_CENTER_URL = "https://my.compscicenter.ru"

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

    def get_site_url(self, **kwargs):
        raise NotImplementedError()
        """Returns site url based on context information"""
        # TODO: Delete after migrating all notifications to new module
        notification = kwargs.pop("notification")
        receiver = notification.user
        if isinstance(notification, AssignmentNotification):
            co = notification.student_assignment.assignment.course
        elif isinstance(notification, CourseNewsNotification):
            co = notification.course_offering_news.course
        else:
            raise NotImplementedError()
        # FIXME: запоминать, с какого сайта отправлено уведомление
        in_club = AcademicRoles.STUDENT_CLUB in receiver.get_cached_groups()
        if in_club or (receiver.is_teacher_club and
                       not receiver.is_teacher_center):
            if co.get_city() == "spb":
                return "http://compsciclub.ru"
            else:
                return "http://{}.compsciclub.ru".format(co.get_city())
        return "https://compscicenter.ru"

    def get_absolute_url(self, url, **kwargs):
        return self.get_site_url(**kwargs) + url
