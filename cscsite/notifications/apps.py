from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        from notifications.signals import notify, notify_handler
        self.module.autodiscover()
        notify.connect(notify_handler,
                       dispatch_uid='notifications.models.notification')
