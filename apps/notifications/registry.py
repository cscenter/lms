from collections.abc import Iterable

from notifications import NotificationTypes


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class NotificationRegistry(object):
    """
    A Notifier object encapsulates an instance of the notifications application
    and used for sending notifications to recipients.
    Models are registered with the Notifier using the register() method.
    """
    def __init__(self):
        self._registry = {}

    def register(self, notification_type, handler_class, **options):
        """
        Registers the given handler.
        If notification already registered, this will raise AlreadyRegistered.
        """

        # TODO: We can register many resolvers instead
        if notification_type in self._registry:
            raise AlreadyRegistered(
                'The notification type {} is already registered. '
                'Skipped.'.format(notification_type, notification_type.name))
        self._registry[notification_type.name] = handler_class()

    def unregister(self, type_or_iterable):
        """
        Unregisters the given notification type(s).

        If a type isn't already registered, this will raise NotRegistered.
        """
        if not isinstance(type_or_iterable, Iterable):
            type_or_iterable = [type_or_iterable]
        for notification_type in type_or_iterable:
            if notification_type not in self._registry:
                raise NotRegistered('The notification type %s is not '
                                    'registered' % notification_type.name)
            del self._registry[notification_type.name]

    def default_handler_class(self):
        return self[NotificationTypes.EMPTY]

    def __contains__(self, notification_type):
        if not isinstance(notification_type, NotificationTypes):
            return False
        return notification_type.name in self._registry

    def __len__(self):
        return len(self._registry)

    def __iter__(self):
        return self._registry

    def __getitem__(self, notification_type):
        if isinstance(notification_type, NotificationTypes):
            code = notification_type.name
        else:
            code = notification_type
        return self._registry[code]

    def items(self):
        return self._registry.items()


registry = NotificationRegistry()
