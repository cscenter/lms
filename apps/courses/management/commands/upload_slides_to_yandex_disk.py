# -*- coding: utf-8 -*-

import datetime

import django_rq
from django.conf import settings
from django.core.management import BaseCommand, CommandError

from courses.models import CourseClass
from courses.tasks import maybe_upload_slides_yandex


class Command(BaseCommand):
    help = """
    Enqueues jobs for uploading course class slides missed on yandex disk.
    """

    def add_arguments(self, parser):
        parser.add_argument('--academic-year', type=int, dest='academic_year')

    def handle(self, *args, **options):
        academic_year = options["academic_year"]
        if academic_year < settings.FOUNDATION_YEAR:
            raise CommandError(f"Academic year should be >= {settings.FOUNDATION_YEAR}")

        queue = django_rq.get_queue('default')
        qs = (CourseClass.objects
              .filter(date__gte=datetime.date(academic_year, month=9, day=1),
                      date__lte=datetime.date(academic_year + 1, month=9, day=1))
              .exclude(slides=""))
        for course_class in qs:
            queue.enqueue(maybe_upload_slides_yandex, course_class.pk)
