# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management import BaseCommand

from learning.models import Semester, CourseOffering


class Command(BaseCommand):
    help = ("Set `is_completed=True` for center courses from past terms. "
            "Provide `--all` also to update club courses.")

    def add_arguments(self, parser):
        parser.add_argument('--all', action="store_true",
                            help='Set to update flag for club site, too')

    def handle(self, *args, **options):
        all_sites = options["all"]
        current_semester = Semester.get_current()
        qs = (CourseOffering.objects
              .filter(semester__index__lt=current_semester.index,
                      is_completed=False))
        if not all_sites:
            qs = qs.exclude(is_open=True)
        qs.update(is_completed=True)
