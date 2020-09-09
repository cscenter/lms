# -*- coding: utf-8 -*-

from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand

from core.timezone import now_local
from core.models import Branch
from projects.constants import REPORTING_NOTIFY_BEFORE_START, \
    REPORTING_NOTIFY_BEFORE_DEADLINE
from projects.models import ReportingPeriod
from notifications import NotificationTypes


class Command(BaseCommand):
    help = """
    Generate notifications about project reporting period boundaries.
    """

    def handle(self, *args, **options):
        for branch in Branch.objects.for_site(site_id=settings.SITE_ID):
            today = now_local(branch.get_timezone()).date()
            # Reminds about start before period actually started
            start_on = today + timedelta(days=REPORTING_NOTIFY_BEFORE_START)
            # Reminds about deadline before period end
            end_on = today + timedelta(days=REPORTING_NOTIFY_BEFORE_DEADLINE)

            notification_type = NotificationTypes.PROJECT_REPORTING_STARTED
            coming_periods = ReportingPeriod.get_periods(start_on=start_on)
            for periods in coming_periods.for_branch(branch).values():
                period = periods[0]  # Periods do not overlap
                if period.students_are_notified(notification_type, branch):
                    continue
                period.generate_notifications(notification_type, branch)

            notification_type = NotificationTypes.PROJECT_REPORTING_ENDED
            ending_periods = ReportingPeriod.get_periods(
                end_on=end_on, start_on__lte=today)
            for periods in ending_periods.for_branch(branch).values():
                period = periods[0]  # Periods do not overlap
                if period.students_are_notified(notification_type, branch):
                    continue
                period.generate_notifications(notification_type, branch)
