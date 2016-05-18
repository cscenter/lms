# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management import BaseCommand

from learning.models import Semester, CourseOffering
from learning.settings import FOUNDATION_YEAR, SEMESTER_TYPES, \
    TERMS_INDEX_START


class Command(BaseCommand):
    help = ("Recalculate system field `index` for Semester model, "
            "which used for ordering and filtering")

    def handle(self, *args, **options):
        max_year = Semester.objects.order_by("-year").first()
        if max_year is None:
            return
        max_year = max_year.year
        index = TERMS_INDEX_START
        for year in range(FOUNDATION_YEAR, max_year + 1):
            for semester_type, _ in SEMESTER_TYPES:
                Semester.objects.filter(year=year, type=semester_type).update(index=index)
                index += 1
