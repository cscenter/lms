# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import csv
import sys

from django.contrib.auth.models import Group
from django.core.management import BaseCommand
from django.utils.encoding import force_bytes

from learning.models import Semester
from users.models import CSCUser


class UnicodeWriter(object):
    def __init__(self, fd, **kwargs):
        self._writer = csv.writer(fd, **kwargs)

    def writerow(self, row):
        self._writer.writerow(list(map(force_bytes, row)))


class Command(BaseCommand):
    help = ("Exports all students along with courses "
            "they've enrolled on into a CSV file.")

    def handle(self, *args, **options):
        w = UnicodeWriter(sys.stdout, dialect=csv.excel_tab)

        current_semester = Semester.objects.first()
        course_offerings = list(current_semester.courseoffering_set
                                .values_list("course__name", flat=True))
        course_offerings.sort()

        w.writerow(["ФИО", "Год поступления"] + course_offerings)

        student_group = Group.objects.get(pk=CSCUser.IS_STUDENT_PK)
        for student in student_group.user_set.all():
            if student.graduation_year or not student.enrollment_year:
                continue

            enrolled_on = set(student.enrolled_on_set
                              .values_list("course__name", flat=True))

            row = [student.get_full_name(), student.enrollment_year]
            for course_offering in course_offerings:
                row.append(int(course_offering in enrolled_on))

            w.writerow(row)

        sys.stdout.flush()

