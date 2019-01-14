from django.apps import AppConfig
from django.utils.functional import cached_property


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        from notifications.signals import notify, notify_handler
        self.module.autodiscover()
        notify.connect(notify_handler,
                       dispatch_uid='notifications.models.notification')

    @cached_property
    def type_map(self):
        """name => id hash map of all notification types fetched from DB"""
        return {t.code: t.id for t in self.get_model('Type').objects.all()}
