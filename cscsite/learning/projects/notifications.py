# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse

from notifications.decorators import register, NotificationType
from notifications.models import Notification
from notifications.notifier import NotificationService


class Type(NotificationType):
    REMINDER = 2


@register(notification_uid=Type.REMINDER)
def test_handler():
    pass


class NewCommentNotification(NotificationService):
    title = "Преподаватель оставил комментарий к отчету {}"
    template = "emails/projects/new_comment.html"

    def get_notifications(self):
        from django.contrib.contenttypes.models import ContentType
        from learning.projects.models import ReportComment, Report
        report_ct = ContentType.objects.get_for_model(Report)
        comment_ct = ContentType.objects.get_for_model(ReportComment)
        return (Notification.objects.unread()
                .filter(
                    action_object_content_type_id=comment_ct.id,
                    target_content_type_id=report_ct.id,
                    emailed=False
                )
                .select_related("recipient")
                .prefetch_related("actor"))

    def get_context(self, notification):
        """
        In theory `project_name` can be already changed,  don't care now.
        """
        report_url = reverse("projects:project_report", kwargs={
            "project_pk": notification.data["project_pk"],
            "student_pk": notification.data["student_pk"]
        })
        return {
            "author": notification.actor.get_full_name(),
            "report_link": self.get_absolute_url(report_url, notification),
            "project_name": notification.data.get("project_name", "")
        }

    def get_msg_subject(self, notification):
        return self.title.format(notification.data["project_name"])

