# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.core.management.base import BaseCommand


from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification


def report(s):
    print("{0} {1}".format(datetime.now().strftime("%Y.%m.%d %H:%M:%S"), s))


class Command(BaseCommand):
    help = "Removes useless notifications"

    def handle(self, *args, **options):
        objects = AssignmentNotification.objects.filter(is_unread=False)
        report("{0} AssignmentNotifications to delete".format(objects.count()))
        objects.delete()
        report("done")
        objects = (CourseOfferingNewsNotification.objects
                   .filter(is_unread=False))
        report("{0} CourseOfferingNewsNotifications to delete"
               .format(objects.count()))
        objects.delete()
        report("done")
