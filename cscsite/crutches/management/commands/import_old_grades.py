# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import csv
from math import ceil
from optparse import make_option
import re

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from learning.models import Enrollment, CourseOffering
from users.models import CSCUser

GRADES_MAPPING = {
    "2": 'unsatisfactory',
    "3": 'pass',
    "4": 'good',
    "5": 'excellent',
    "зачёт": 'pass',
    "незачёт": 'unsatisfactory'
}

class Command(BaseCommand):
    args = '<csv_path>'
    help = 'Imports old grades into our database from CSV file'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("csv path is needed")
        csv_path = args[0]
        with open(csv_path, 'rb') as f:
            reader = csv.DictReader(f)
            success = 0
            co_index = {}
            for fname_bin in reader.fieldnames:
                fname = fname_bin.decode('utf8')
                if (fname in {"Фамилия", "Имя"}
                    or fname.startswith("Внешни")):
                    continue
                m = re.search("(?P<course_slug>[-\w]+)/"
                              "(?P<semester_slug>[-\w]+)/",
                              fname)
                if not m:
                    self.stdout.write("bad column name: {}".format(fname))
                    return
                year, type_ = m.group('semester_slug').split("-")
                year = int(year)
                course_slug = m.group('course_slug')
                try:
                    co = CourseOffering.objects.get(course__slug=course_slug,
                                                    semester__year=year,
                                                    semester__type=type_)
                    co_index[fname] = co
                except ObjectDoesNotExist:
                    self.stdout.write("No CourseOffering for {}, {}, {}"
                                      .format(course_slug, type_, year))
                    #return
                #co_index[fname] = co

            for entry in reader:
                entry = {k.decode('utf8'): v.decode('utf8')
                         for k, v in entry.items()}
                last_name = entry['Фамилия']
                first_name = entry['Имя']
                users = list(CSCUser.objects
                             .filter(last_name=last_name,
                                     first_name=first_name))
                if len(users) < 1:
                    self.stdout.write("ERROR: no user named {} {}"
                                      .format(first_name, last_name))
                    continue
                if len(users) > 1:
                    self.stdout.write("ERROR: more than one user named {} {}"
                                      .format(first_name, last_name)
                                      .encode('utf8'))
                    continue
                student = users[0]
                for k, v in entry.items():
                    if k not in co_index:
                        continue
                    if v is '':
                        continue
                    grade = GRADES_MAPPING.get(v)
                    co = co_index[k]
                    if not grade:
                        self.stdout.write("ERROR: can't map grade {}"
                                          .format(v)
                                          .encode('utf8'))
                        continue
                    enr, created = (Enrollment.objects
                                    .get_or_create(
                                        student=student,
                                        course_offering=co,
                                        defaults={'grade': grade}))
                    enr.save()
                    self.stdout.write("INFO: grade '{}' set for user {} on {} "
                                      "(created: {})"
                                      .format(grade, student, co, created))
                    success += 1
            self.stdout.write("{} successes".format(success))
