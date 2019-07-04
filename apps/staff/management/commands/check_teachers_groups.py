# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management import BaseCommand

from courses.models import Course
from users.constants import AcademicRoles
from users.models import User


class Command(BaseCommand):
    help = "Update teachers groups based on data from course info"

    CENTER_ONLY = 1
    CLUB_ONLY = 2
    BOTH = 3

    def handle(self, *args, **options):
        teachers = {}
        cos = Course.objects.prefetch_related("teachers")
        for co in cos:
            for teacher in co.teachers.all():
                if teacher.pk not in teachers:
                    teachers[teacher.pk] = {
                        "state": self.CLUB_ONLY if co.is_open else self.CENTER_ONLY,
                        "obj": teacher
                    }
                if teachers[teacher.pk]["state"] == self.BOTH:
                    continue
                if teachers[teacher.pk]["state"] == self.CENTER_ONLY and co.is_open:
                    teachers[teacher.pk]["state"] = self.BOTH
                elif teachers[teacher.pk]["state"] == self.CLUB_ONLY and not co.is_open:
                    teachers[teacher.pk]["state"] = self.BOTH
        # Ok, try to update teacher groups, looks as hell, but it works
        for teacher in teachers:
            if teachers[teacher]["state"] == self.BOTH:
                teachers[teacher]["obj"].add_group(AcademicRoles.TEACHER)
                teachers[teacher]["obj"].add_group(AcademicRoles.TEACHER_CLUB)
            elif teachers[teacher]["state"] == self.CLUB_ONLY:
                teachers[teacher]["obj"].add_group(AcademicRoles.TEACHER_CLUB)
                teachers[teacher]["obj"].remove_group(AcademicRoles.TEACHER)
            elif teachers[teacher]["state"] == self.CENTER_ONLY:
                teachers[teacher]["obj"].add_group(AcademicRoles.TEACHER)
                teachers[teacher]["obj"].remove_group(AcademicRoles.TEACHER_CLUB)
