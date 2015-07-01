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
    help = ("Get students without expelled status")

    def handle(self, *args, **options):
        w = unicodecsv.writer(sys.stdout, encoding='utf-8')

        current_semester = Semester.objects.first()

        students = (CSCUser.objects
            .filter(
                groups__in=[CSCUser.group_pks.STUDENT_CENTER],
                enrollment_year__isnull=False,
                graduation_year__isnull=True,
            )
            .exclude(
                groups__in=[CSCUser.group_pks.GRADUATE_CENTER],
            )
            .exclude(
                status__in=[CSCUser.STATUS.will_graduate, 'expelled']
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
            w.writerow([student.get_full_name(), student.yandex_id, student.enrollment_year, len(student.enrollments), student.id])

        sys.stdout.flush()
