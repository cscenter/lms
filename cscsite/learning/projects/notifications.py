# -*- coding: utf-8 -*-
from notifications.decorators import register
from notifications.models import Notification
from notifications.notifier import NotificationConfig


@register()
class NewCommentNotification(NotificationConfig):
    title = "Преподаватель оставил комментарий к решению задания"
    template = "emails/new_comment_for_student.html"

    def get_notifications(self):
        return Notification.objects.unread()

    def notify(self, notification):
        pass

    def get_context(self, notification):
        pass

