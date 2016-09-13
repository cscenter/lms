# -*- coding: utf-8 -*-


def register(config_class):
    """
    Registers the given config class.

    If the config class is already registered, this will raise an exception.

    Example:
        from notifications.notifier import NotificationConfig

        @register
        class ProjectNotification(NotificationConfig):
            pass
    """
    from notifications.notifier import notifier, NotificationConfig

    if not issubclass(config_class, NotificationConfig):
        raise ValueError('Wrapped class must subclass NotificationConfig.')
    notifier.register(config_class)
    return config_class
