from djchoices import ChoiceItem, DjangoChoices

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationQuerySet(models.query.QuerySet):

    def unread(self, include_deleted=False):
        """Return only unread items in the current queryset"""
        if not include_deleted:
            return self.filter(unread=True, deleted=False)
        else:
            # To improve query performance, don't filter by 'deleted' field
            return self.filter(unread=True)

    def read(self, include_deleted=False):
        """Return only read items in the current queryset"""
        if not include_deleted:
            return self.filter(unread=False, deleted=False)
        else:
            # To improve query performance, don't filter by 'deleted' field
            return self.filter(unread=False)

    def mark_all_as_read(self, recipient=None):
        """Mark as read any unread messages in the current queryset.

        Optionally, filter these by recipient first.
        """
        # We want to filter out read ones, as later we will store
        # the time they were marked as read.
        qs = self.unread(True)
        if recipient:
            qs = qs.filter(recipient=recipient)

        return qs.update(unread=False)

    def mark_all_as_unread(self, recipient=None):
        """Mark as unread any read messages in the current queryset.

        Optionally, filter these by recipient first.
        """
        qs = self.read(True)

        if recipient:
            qs = qs.filter(recipient=recipient)

        return qs.update(unread=True)

    def deleted(self):
        """Return only deleted items in the current queryset"""
        return self.filter(deleted=True)

    def active(self):
        """Return only active(un-deleted) items in the current queryset"""
        return self.filter(deleted=False)

    def mark_all_as_deleted(self, recipient=None):
        """Mark current queryset as deleted.
        Optionally, filter by recipient first.
        """
        qs = self.active()
        if recipient:
            qs = qs.filter(recipient=recipient)

        return qs.update(deleted=True)

    def mark_all_as_active(self, recipient=None):
        """Mark current queryset as active(un-deleted).
        Optionally, filter by recipient first.
        """
        qs = self.deleted()
        if recipient:
            qs = qs.filter(recipient=recipient)

        return qs.update(deleted=False)


class Type(models.Model):
    code = models.CharField(max_length=255, unique=True)
    deleted = models.BooleanField(
        default=False,
        help_text=_("""Check if you want to save
        related notifications in DB, but show,
        that you are not using this notification type anymore."""))

    class Meta:
        verbose_name = _("Type")
        verbose_name_plural = _("Types")

    def __str__(self):
        return self.code


class Notification(models.Model):
    """
    Action model describing the actor acting out a verb (on an optional
    target).
    Nomenclature based on http://activitystrea.ms/specs/atom/1.0/

    Generalized Format::

        <actor> <verb> <time>
        <actor> <verb> <target> <time>
        <actor> <verb> <action_object> <target> <time>

    Examples::

        <justquick> <reached level 60> <1 minute ago>
        <brosner> <commented on> <pinax/pinax> <2 hours ago>
        <washingtontimes> <started follow> <justquick> <8 minutes ago>
        <mitsuhiko> <closed> <issue 70> on <mitsuhiko/flask> <about 2 hours ago>

    Unicode Representation::

        justquick reached level 60 1 minute ago
        mitsuhiko closed issue 70 on mitsuhiko/flask 3 hours ago

    HTML Representation::

        <a href="http://oebfare.com/">brosner</a> commented on <a href="http://github.com/pinax/pinax">pinax/pinax</a> 2 hours ago

    """

    # Note: not used at all
    class LevelTypes(DjangoChoices):
        success = ChoiceItem()
        info = ChoiceItem()
        warning = ChoiceItem()
        error = ChoiceItem()

    level = models.CharField(choices=LevelTypes.choices,
                             default=LevelTypes.info,
                             max_length=20)

    type = models.ForeignKey(
        Type,
        related_name="+",  # Don't create a backwards relation
        on_delete=models.CASCADE)

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL,
                                  blank=True,
                                  null=True,
                                  related_name='notifications',
                                  on_delete=models.CASCADE)
    unread = models.BooleanField(default=True, blank=False)

    actor_content_type = models.ForeignKey(ContentType,
                                           related_name='notify_actor',
                                           blank=True, null=True,
                                           on_delete=models.CASCADE)
    actor_object_id = models.PositiveIntegerField(blank=True, null=True)
    actor = GenericForeignKey('actor_content_type', 'actor_object_id')

    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    target_content_type = models.ForeignKey(ContentType,
                                            related_name='notify_target',
                                            blank=True,
                                            null=True,
                                            on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField(blank=True, null=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    action_object_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        related_name='notify_action_object',
        on_delete=models.CASCADE)
    action_object_object_id = models.PositiveIntegerField(blank=True, null=True)
    action_object = GenericForeignKey('action_object_content_type',
                                      'action_object_object_id')

    timestamp = models.DateTimeField(default=timezone.now)

    # System notification if not public
    public = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False)

    data = models.JSONField(blank=True, null=True)
    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ('-timestamp', )
        app_label = 'notifications'
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.timestamp, now)

    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save()

    def mark_as_unread(self):
        if not self.unread:
            self.unread = True
            self.save()

