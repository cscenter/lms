# -*- coding: utf-8 -*-

from datetime import timedelta

from django.apps import apps
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from courses.models import Semester
from learning.projects.models import ProjectStudent
from learning.settings import DATE_FORMAT_RU, GradeTypes
from notifications import types
from notifications.models import Notification
from notifications.signals import notify


class Command(BaseCommand):
    help = """
    Generate notifications when project reporting period started or ended.
    """

    # TODO: add tests
    def handle(self, *args, **options):
        """
        When we check notifications existence, check count only, because we
        insert notifications inside transaction
        """
        current_term = Semester.get_current()
        today = now()
        notification_type_map = apps.get_app_config('notifications').type_map
        remind_about_start_today = (current_term.report_starts_at and
            today.date() == current_term.report_starts_at - timedelta(days=3))
        remind_about_end_today = (current_term.report_ends_at and
            today.date() == current_term.report_ends_at - timedelta(days=1))
        if remind_about_start_today:
            notification_code = types.PROJECT_REPORTING_STARTED.name
            notification_type_id = notification_type_map[notification_code]
            # Check notifications since term start
            filters = dict(
                type_id=notification_type_id,
                timestamp__gte=current_term.starts_at
            )
            if Notification.objects.filter(**filters).count() > 0:
                return
            self.generate_notifications(current_term,
                                        types.PROJECT_REPORTING_STARTED)
        elif remind_about_end_today:
            notification_code = types.PROJECT_REPORTING_ENDED.name
            notification_type_id = notification_type_map[notification_code]
            # Check notifications since reporting period start
            filters = dict(
                type_id=notification_type_id,
                timestamp__date__gte=current_term.report_starts_at
            )
            if Notification.objects.filter(**filters).count() > 0:
                return
            self.generate_notifications(current_term,
                                        types.PROJECT_REPORTING_ENDED)

    @transaction.atomic
    def generate_notifications(self, term, notification_type):
        """
        Generate notifications of selected type for students without
        sent report
        """
        project_students = (ProjectStudent.objects
                            .filter(project__semester=term,
                                    project__canceled=False,
                                    report__isnull=True)
                            .exclude(final_grade=GradeTypes.UNSATISFACTORY)
                            .select_related("student", "project")
                            .distinct()
                            .all())
        context = {
            "period_start": term.report_starts_at.strftime(DATE_FORMAT_RU),
            "deadline": term.report_ends_at.strftime(DATE_FORMAT_RU),
        }
        for ps in project_students:
            context.update({
                "project_id": ps.project_id
            })
            notify.send(
                sender=None,  # actor
                type=notification_type,
                verb='was sent',
                target=term,
                recipient=ps.student,
                data=context
            )
