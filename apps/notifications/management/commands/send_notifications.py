# -*- coding: utf-8 -*-
import logging

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation
from django.utils.decorators import method_decorator

from core.locks import distributed_lock, get_shared_connection
from notifications import NotificationTypes
from notifications.models import Notification
from notifications.registry import registry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    # FIXME: Actually only project notifications
    help = 'Send generic email notifications'
    can_import_settings = True

    @method_decorator(distributed_lock('notify-lock', timeout=600,
                                       get_client=get_shared_connection))
    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        unread_notifications = (Notification.objects
                                .unread()
                                .filter(public=True, emailed=False)
                                .select_related("recipient"))
        # FIXME: Refactor
        # id => code
        types_map = {v: k for k, v in
                     apps.get_app_config('notifications').type_map.items()}
        # TODO: skip EMPTY type notifications?
        for notification in unread_notifications:
            try:
                code = types_map[notification.type_id]
            except KeyError:
                # On notification type deletion, we should cascading
                # delete all notifications, low chance of error this type.
                logger.error("Couldn't map code to type_id {}. "
                             "Mark as deleted.".format(notification.type_id))
                Notification.objects.filter(pk=notification.pk).update(
                    deleted=True)
                continue
            notification_type = getattr(NotificationTypes, code)
            if notification_type in registry:
                registry[code].notify(notification)
            else:
                logger.warning("Handler for type '{}' not registered. "
                               "Mark as deleted.".format(code))
                Notification.objects.filter(pk=notification.pk).update(
                    deleted=True)

        translation.deactivate()
