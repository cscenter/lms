# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime

import django_rq

from django.core.management import BaseCommand
from django.core.management import CommandError

from learning import settings
from courses.models import CourseClass
from learning.tasks import maybe_upload_slides_yandex


class Command(BaseCommand):
    help = """
    Try to reupload course class slides stored locally, but missed on
    yandex disk for passed period beginning.

    """

    def add_arguments(self, parser):
        parser.add_argument('--period_start', type=int,
                            dest='year_start',
                            help='Remote path includes folder with academic '
                                 'years, pass 2015 and slides will be '
                                 'uploaded to `2015-2016` folder')

    def handle(self, *args, **options):
        year_start = options["year_start"]
        if year_start < settings.FOUNDATION_YEAR:
            raise CommandError("period should starts from {}".format(
                settings.FOUNDATION_YEAR))

        qs = (CourseClass.objects
              .filter(date__gte=datetime.date(year_start, month=9, day=1),
                      date__lte=datetime.date(year_start + 1, month=9, day=1))
              .exclude(slides=""))
        queue = django_rq.get_queue('default')
        for course_class in qs:
            queue.enqueue(maybe_upload_slides_yandex, course_class.pk)
