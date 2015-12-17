# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management import BaseCommand

from learning.models import Semester, CourseOffering


class Command(BaseCommand):
    help = ("Set flag is_completed=True for courses from past semesters")

    def handle(self, *args, **options):
        current_semester = Semester.get_current()
        CourseOffering.objects.exclude(semester=current_semester).update(
            is_completed=True)
