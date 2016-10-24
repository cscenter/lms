# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse

from notifications.decorators import register
from notifications.service import NotificationService
from notifications import types


@register(notification_type=types.NEW_PROJECT_REPORT)
class NewReport(NotificationService):
    """
    Student <actor> sent <verb> Report <action_object> on project" <target>

    Models:
        actor - CSCUser
        action_object - Report
        target - Project
    """

    subject = "{} отправил отчёт по проекту"
    template = "emails/projects/new_report.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_subject(self, notification, **kwargs):
        return self.subject.format(notification.actor.get_full_name())

    def get_context(self, notification):
        report_url = reverse("projects:project_report", kwargs={
            "project_pk": notification.data["project_pk"],
            "student_pk": notification.data["student_pk"]
        })
        project_url = reverse("projects:student_project_detail",
                              args=[notification.data["project_pk"]])
        return {
            "author": notification.actor.get_full_name(),
            "project_name": notification.data.get("project_name", ""),
            "project_link": self.get_absolute_url(project_url),
            "report_link": self.get_absolute_url(report_url),
        }
        # Low chance project name will be updated

    # TODO: make as default implementation?
    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


@register(notification_type=types.NEW_PROJECT_REPORT_COMMENT)
class NewReportComment(NotificationService):
    """
    Student <actor> added <verb> comment <action_object> on
    "Report for project" <target>

    Models:
        actor - CSCUser
        action_object - ReportComment
        target - Report
    """

    subject = "Новый комментарий к отчёту по проекту {} ({})"
    template = "emails/projects/new_comment.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_subject(self, notification, **kwargs):
        return self.subject.format(notification.data["project_name"],
                                   notification.actor.get_full_name())

    def get_context(self, notification):
        """
        In theory `project_name` can be already changed,  don't care now.
        """
        report_url = reverse("projects:project_report", kwargs={
            "project_pk": notification.data["project_pk"],
            "student_pk": notification.data["student_pk"]
        })
        project_url = reverse("projects:student_project_detail",
                              args=[notification.data["project_pk"]])
        return {
            "author": notification.actor.get_full_name(),
            "project_name": notification.data.get("project_name", ""),
            "project_link": self.get_absolute_url(project_url),
            "report_link": self.get_absolute_url(report_url),
        }

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


@register(notification_type=types.PROJECT_REPORT_IN_REVIEW_STATE)
class ReportInReviewState(NotificationService):
    """
    Curator <actor> changed <verb> status on "Report for project" <target>
    to "review". This means project reviewers can see report now and assess it.

    Models:
        actor - CSCUser
        action_object - <None>
        target - Report
    """

    subject = "Отчет по проекту «{}» доступен для проверки"
    template = "emails/projects/report_review_state.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_subject(self, notification, **kwargs):
        return self.subject.format(notification.data["project_name"])

    def get_context(self, notification):
        return notification.data

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


@register(notification_type=types.PROJECT_REPORT_REVIEWING_COMPLETED)
class ReviewCompleted(NotificationService):
    """
    Curator <actor> sent email <verb> to Student <recipient>
    that reviewing <target> of project report completed

    Models:
        actor - CSCUser
        action_object - <None>
        target - Report
    """

    subject = "Результаты проверки отчёта"
    template = "emails/projects/report_completed.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_context(self, notification):
        return notification.data

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL

    @staticmethod
    def get_reply_to():
        return "practice@compscicenter.ru"


@register(notification_type=types.PROJECT_REPORTING_STARTED)
class ProjectReportingStarted(NotificationService):
    """
    Was sent notification <action_object> about the beginning of the
    reporting period <verb> for Semester <target> to Student <recipient>

    Models:
        action_object - None/self
        target - Semester (not sure)
    """

    subject = "Время присылать отчёты по практике"
    template = "emails/projects/report_period_start.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification [report_ending] was generated "
                          "for recipient {}".format(notification.recipient))
        notification.save()

    def get_context(self, notification):
        context = notification.data
        context["project_url"] = reverse("projects:student_project_detail",
                                         args=[notification.data["project_id"]])
        return context

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


@register(notification_type=types.PROJECT_REPORTING_ENDED)
class ProjectReportingEnded(NotificationService):
    """
    Was sent notification <action_object> about the ending of the
    reporting period <verb> for Semester <target> to Student <recipient>

    Models:
        action_object - None/self
        target - Semester (not sure)
    """

    subject = "До сдачи отчёта остался один день"
    template = "emails/projects/report_period_end.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification [report_ending] was generated "
                          "for recipient {}".format(notification.recipient))
        notification.save()

    def get_context(self, notification):
        context = notification.data
        context["project_url"] = reverse("projects:student_project_detail",
                                         args=[notification.data["project_id"]])
        return context

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL