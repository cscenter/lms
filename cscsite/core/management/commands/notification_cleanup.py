# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import smart_text
from django.utils.html import strip_tags, linebreaks

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
