from notifications.decorators import register
from notifications.service import NotificationService
from notifications import types


@register(notification_type=types.EMPTY)
class EmptyNotification(NotificationService):
    """
    Default service to queue any registered notification,
    don't know how to process them.
    """
    subject = None
    template = None

    def add_to_queue(self, notification, **kwargs):
        notification.save()

    def notify(self, notification):
        pass


@register(notification_type=types.LOG)
class LogNotification(NotificationService):
    subject = None
    template = None

    def add_to_queue(self, notification, **kwargs):
        notification.save()

    def notify(self, notification):
        pass
