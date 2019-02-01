# -*- coding: utf-8 -*-

from core.urls import reverse
from learning.projects.models import ReportComment, Report
from notifications import types
from notifications.decorators import register
from notifications.service import NotificationService
from users.models import User


@register(notification_type=types.NEW_PROJECT_REPORT)
class NewReport(NotificationService):
    """
    Student <actor> sent <verb> Report <action_object> on project" <target>

    Models:
        actor - User
        action_object - Report
        target - Project
    """

    subject = "{} отправил{} отчёт по проекту"
    template = "emails/projects/new_report.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_subject(self, notification, **kwargs):
        return self.subject.format(
            notification.actor.get_full_name(),
            "а" if notification.actor.gender == User.GENDER_FEMALE else ""
        )

    def get_context(self, notification):
        report_url = reverse("projects:project_report", kwargs={
            "project_pk": notification.data["project_pk"],
            "student_pk": notification.data["student_pk"]
        })
        project_url = reverse("projects:project_detail",
                              args=[notification.data["project_pk"]])
        author_declension = ""
        if notification.actor.gender == User.GENDER_FEMALE:
            author_declension = "a"
        return {
            "author": notification.actor.get_full_name(),
            "author_declension": author_declension,
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
        actor - User
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
        # Fetch comment from db
        c = (ReportComment.objects
             .only("text", "attached_file")
             .get(pk=notification.action_object_object_id))
        student_id = notification.data.get("student_id", False)
        notification_for_student = (student_id == notification.recipient_id)
        if notification_for_student:
            report_url_name = "projects:student_project_report"
            project_url_name = "projects:student_project_detail"
        else:
            report_url_name = "projects:project_report"
            project_url_name = "projects:project_detail"
        report_url = reverse(report_url_name, kwargs={
            "project_pk": notification.data["project_pk"],
            "student_pk": notification.data["student_pk"]
        })
        project_url = reverse(project_url_name,
                              args=[notification.data["project_pk"]])
        author_declension = ""
        if notification.actor.gender == User.GENDER_FEMALE:
            author_declension = "a"
        context = {
            "author": notification.actor.get_full_name(),
            "author_declension": author_declension,
            "project_name": notification.data.get("project_name", ""),
            "project_link": self.get_absolute_url(project_url),
            "report_link": self.get_absolute_url(report_url),
            "message": c.text,
            "has_attach": bool(c.attached_file)
        }

        return context

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


@register(notification_type=types.PROJECT_REPORTS_IN_REVIEW_STATE)
class ReportInReviewState(NotificationService):
    """
    Curator <actor> changed <verb> status on "Report for project" <target>
    to "review". This means project reviewers can see report now and assess it.

    Models:
        actor - User
        action_object - <None>
        target - Report
    """

    subject = "Можно приступать к проверке отчетов проекта"
    template = "emails/projects/reviewers_can_view_project_reports.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_context(self, notification):
        context = notification.data
        project_url = reverse("projects:project_detail",
                              args=[notification.data["project_pk"]])
        context["project_link"] = self.get_absolute_url(project_url)
        reports = []
        for student_id, student_name in context["reports"]:
            report_url = reverse("projects:project_report", kwargs={
                "project_pk": context["project_pk"],
                "student_pk": student_id
            })
            reports.append((student_name, self.get_absolute_url(report_url)))
        context["reports"] = reports
        return context

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


@register(notification_type=types.PROJECT_REPORT_COMPLETED)
class ReportCompleted(NotificationService):
    """
    Curator <actor> sent email <verb> to Student <recipient>
    that assessment of project report <target> completed

    Models:
        actor - User
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


@register(notification_type=types.PROJECT_REPORT_REVIEW_COMPLETED)
class ReviewCompleted(NotificationService):
    """
    Reviewer <actor> complete <verb> review <action_object> on "Report" <target>

    Models:
        actor - User
        action_object - Review
        target - Report
    """

    subject = "{} завершил{} проверку отчёта"
    template = "emails/projects/review_completed.html"

    def add_to_queue(self, notification, *args, **kwargs):
        self.logger.debug("Notification was generated for recipient {}".format(
            notification.recipient
        ))
        notification.save()

    def get_context(self, notification):
        context = notification.data
        project_url = reverse("projects:project_detail",
                              args=[notification.data["project_pk"]])
        report_url = reverse("projects:project_report", kwargs={
            "project_pk": notification.data["project_pk"],
            "student_pk": notification.data["student_pk"]
        })
        context["project_link"] = self.get_absolute_url(project_url)
        context["report_link"] = self.get_absolute_url(report_url)
        context["reviewer"] = notification.actor.get_full_name()
        # Get other reports data (name, link, status)
        reports = []
        rs = (Report.objects
              .filter(pk__in=context["other_reports"])
              .select_related("project_student__student"))
        for r in rs:
            report_url = reverse("projects:project_report", kwargs={
                "project_pk": notification.data["project_pk"],
                "student_pk": r.project_student.student.pk
            })
            row = (r.project_student.student.get_full_name(),
                   self.get_absolute_url(report_url),
                   r.get_status_display())
            reports.append(row)
        context["other_reports"] = reports
        return context

    def get_subject(self, notification, **kwargs):
        reviewer = notification.actor.get_full_name()
        reviewer_declension = ""
        if notification.actor.gender == User.GENDER_FEMALE:
            reviewer_declension = "a"
        return self.subject.format(reviewer, reviewer_declension)

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL


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
        self.logger.debug("Notification [report_start] was generated "
                          "for recipient {}".format(notification.recipient))
        notification.save()

    def get_context(self, notification):
        context = notification.data
        project_url = reverse("projects:student_project_detail",
                              args=[notification.data["project_id"]])
        context["project_link"] = self.get_absolute_url(project_url)
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
        project_url = reverse("projects:student_project_detail",
                              args=[notification.data["project_id"]])
        context["project_link"] = self.get_absolute_url(project_url)
        return context

    def get_site_url(self, **kwargs):
        return self.SITE_CENTER_URL