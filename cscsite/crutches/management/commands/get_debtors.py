# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import csv
import sys
import unicodecsv

from django.core.management import BaseCommand

from learning.models import Semester, Enrollment
from users.models import CSCUser
from django.db.models import Count, Prefetch


class Command(BaseCommand):
    help = ("Show potencial debtors with insufficient number of passed courses."
            " Courses amount should be >= 2n, where n - number of semesters "
            "student studying")

    def handle(self, *args, **options):
        w = unicodecsv.writer(sys.stdout, encoding='utf-8',
            dialect=csv.excel_tab)

        current_semester = Semester.objects.first()

        students = (CSCUser.objects
            .filter(
                groups__in=[CSCUser.group_pks.STUDENT_CENTER],
                enrollment_year__isnull=False,
                graduation_year__isnull=True
            )
            .prefetch_related(
                Prefetch(
                    'enrollment_set',
                    queryset=Enrollment.objects
                        .exclude(grade__in=['not_graded', 'unsatisfactory'])
                        .select_related('course_offering',
                                        'course_offering__semester',
                                        'course_offering__course'
                                        ),
                    to_attr='enrollments'
                ),
            )
        )

        for student in students:
            # Count semesters
            student_semesters_cnt = \
                (current_semester.year - student.enrollment_year) * 2
            if current_semester.type == Semester.TYPES.autumn:
                student_semesters_cnt += 1
            if len(student.enrollments) < student_semesters_cnt * 2:
                w.writerow([student.get_full_name(), "https://compscicenter.ru/users/{}/".format(student.id)])

        sys.stdout.flush()
