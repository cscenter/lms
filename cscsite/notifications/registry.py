from collections import Iterable

from notifications.notifier import AlreadyRegistered, NotRegistered


class NotificationRegistry(object):
    """
    A Notifier object encapsulates an instance of the notifications application
    and used for sending notifications to recipients.
    Models are registered with the Notifier using the register() method.
    """
    def __init__(self):
        self._registry = {}

    def register(self, notification_id, signal_handler, **options):
        """
        Registers the given handler.
        If notification already registered, this will raise AlreadyRegistered.
        """

        if notification_id in self._registry:
            raise AlreadyRegistered(
                'The notification with uid={} is already registered. Type {} '
                'skiped.'.format(notification_id, str(notification_id)))
        self._registry[notification_id] = signal_handler

    def unregister(self, type_or_iterable):
        """
        Unregisters the given notification type(s).

        If a type isn't already registered, this will raise NotRegistered.
        """
        if not isinstance(type_or_iterable, Iterable):
            type_or_iterable = [type_or_iterable]
        for notification_uid in type_or_iterable:
            if notification_uid not in self._registry:
                raise NotRegistered('The notification type %s is not '
                                    'registered' % str(notification_uid))
            del self._registry[notification_uid]

    def is_registered(self, notification_uid):
        """
        Check if a notification type is registered with this `Notifier`.
        """
        return notification_uid in self._registry

    def __iter__(self):
        return self._registry

    def __len__(self):
        return len(self._registry)

    def items(self):
        return self._registry.items()

    def __getitem__(self, item):
        return self._registry[item]


registry = NotificationRegistry()
