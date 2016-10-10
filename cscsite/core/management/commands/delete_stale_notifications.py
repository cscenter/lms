# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand

from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification, Semester


class Command(BaseCommand):
    help = "Delete notifications from past terms"

    def handle(self, *args, **options):
        current_term = Semester.get_current()
        AssignmentNotification.objects.filter(
            created__lt=current_term.starts_at).delete()
        CourseOfferingNewsNotification.objects.filter(
            created__lt=current_term.starts_at).delete()
        print("done")
