# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from courses.models import Semester
from learning.models import AssignmentNotification, CourseNewsNotification


class Command(BaseCommand):
    help = "Soft delete for notifications from the past terms"

    def handle(self, *args, **options):
        current_term = Semester.get_current()
        updated = (AssignmentNotification.objects
                   .filter(created__lt=current_term.starts_at, is_unread=True)
                   .update(is_unread=False))
        msg = f"{updated} AssignmentNotifications are marked as read"
        self.stdout.write(msg)
        updated = (CourseNewsNotification.objects
                   .filter(created__lt=current_term.starts_at, is_unread=True)
                   .update(is_unread=False))
        msg = f"{updated} CourseNewsNotifications are marked as read"
        self.stdout.write(msg)
