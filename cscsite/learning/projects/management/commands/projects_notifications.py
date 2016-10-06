# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.apps import apps
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from learning.models import Semester
from learning.projects.models import ProjectStudent
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
        type_map = apps.get_app_config('notifications').type_map
        if current_term.report_starts_at == today.date():
            notification_code = types.PROJECT_REPORTING_STARTED.name
            notification_type_id = type_map[notification_code]
            # Check notifications since term start
            filters = dict(
                type_id=notification_type_id,
                timestamp__gte=current_term.starts_at
            )
            if Notification.objects.filter(**filters).count() > 0:
                return
            self.generate_notifications(current_term,
                                        types.PROJECT_REPORTING_STARTED)
        elif current_term.report_ends_at == today.date():
            notification_code = types.PROJECT_REPORTING_ENDED.name
            notification_type_id = type_map[notification_code]
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
                                    report__isnull=True)
                            .select_related("student")
                            .distinct()
                            .all())
        for ps in project_students:
            notify.send(
                sender=None,  # actor
                type=notification_type,
                verb='was sent',
                target=term,
                recipient=ps.student,
                # Unmodified context
                data={
                    "semester_name": str(term),
                    "deadline": term.report_ends_at,
                }
            )
