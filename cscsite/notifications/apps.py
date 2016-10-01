from django.apps import AppConfig

from notifications.decorators import NotificationType


class Type(NotificationType):
    EMPTY = 0
    SYSTEM = 1


def empty(*args, **kwargs):
    pass


def system_handler(*args, **kwargs):
    pass


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        from notifications.signals import notify
        from notifications.signals import notify_handler
        self.module.registry.register(Type.EMPTY, empty)
        self.module.registry.register(Type.SYSTEM, system_handler)
        self.module.autodiscover()
        notify.connect(notify_handler,
                       dispatch_uid='notifications.models.notification')
