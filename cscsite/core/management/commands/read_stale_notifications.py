# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification, Semester


class Command(BaseCommand):
    help = "Soft delete for notifications from past terms"

    def handle(self, *args, **options):
        current_term = Semester.get_current()
        AssignmentNotification.objects.filter(
            created__lt=current_term.starts_at, is_unread=True).update(is_unread=False)
        CourseOfferingNewsNotification.objects.filter(
            created__lt=current_term.starts_at, is_unread=True).update(is_unread=False)
        print("done")
