# -*- coding: utf-8 -*-
from enum import IntEnum


class NotificationType(IntEnum):
    """Enumerate all available notification types"""

    def __init__(self, *args):
        # Restrict by positive int
        if self.value < 0:
            raise ValueError("NotificationType must be positive")
        # Disallow duplication
        cls = self.__class__
        if any(self.value == e.value for e in cls):
            a = self.name
            e = cls(self.value).name
            raise ValueError("aliases not allowed in NotificationType:  "
                             "%r --> %r" % (a, e))


def register(notification_uid):
    """
    Registers the given notification uid and associated signal handler.

    If the notification uid is already registered, this will raise an exception.

    Example:
        from notifications.decorators import register, NotificationType

        class Types(NotificationType):
            TEST_UID = 1

        @register(notification_uid=Types.TEST_UID)
        def test_handler(*args, **kwargs):
            pass
    """
    from notifications.registry import registry as notification_registry

    if not isinstance(notification_uid, NotificationType):
        raise ValueError('notification_uid must subclass NotificationType.')

    def wrapper(signal_handler):
        notification_registry.register(notification_uid, signal_handler)
        return signal_handler
    return wrapper
