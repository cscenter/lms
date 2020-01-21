# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from courses.models import Semester
from courses.utils import get_term_index


class Command(BaseCommand):
    help = "Recalculates `Semester.index` values used for ordering/filtering"

    def handle(self, *args, **options):
        for term in Semester.objects.all():
            term.index = get_term_index(term.year, term.type)
            term.save(update_fields=['index'])
