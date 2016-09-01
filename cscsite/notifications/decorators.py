# -*- coding: utf-8 -*-


def register(**options):
    """
    Registers the given config class with the given options.

    If the config class is already registered, this will raise an exception.

    Example:
        from notifications.notifier import NotificationConfig

        @register(backend='django.core.mail.backends.smtp.EmailBackend')
        class ProjectNotification(NotificationConfig):
            pass
    """
    from notifications.notifier import notifier, NotificationConfig

    def wrapper(config_class):
        if not issubclass(config_class, NotificationConfig):
            raise ValueError('Wrapped class must subclass NotificationConfig.')
        notifier.register(config_class, **options)

    return wrapper
