# -*- coding: utf-8 -*-
from notifications import NotificationTypes
from notifications.registry import registry as notification_registry
from notifications.service import NotificationService


def register(notification_type):
    """
    Registers the given notification type and associated handler.

    If the notification type is already registered,
    this will raise an exception.

    Example:
        from notifications import types
        from notifications.decorators import register
        from notifications.service import NotificationService

        @register(notification_type=types.LOG)
        class LogNotificationHandler(NotificationService):
            pass
    """

    if not isinstance(notification_type, NotificationTypes):
        raise ValueError('notification type must be instance of '
                         'NotificationTypes.')

    def wrapper(service_cls):
        if not issubclass(service_cls, NotificationService):
            raise ValueError('Wrapped class must subclass NotificationService.')
        notification_registry.register(notification_type, service_cls)
        return service_cls
    return wrapper
