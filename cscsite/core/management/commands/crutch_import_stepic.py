# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import csv
from math import ceil
from optparse import make_option

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from learning.models import AssignmentStudent, Assignment
from users.models import CSCUser

class Command(BaseCommand):
    args = '<csv_path assignment_id>'
    help = 'Imports Stepic grades into our database from CSV file'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("csv path and assignment id are needed")
        csv_path, a_id = args
        try:
            a = Assignment.objects.get(pk=a_id)
        except ObjectDoesNotExist:
            raise CommandError("No assignment with id {}".format(a_id))
        with open(csv_path, 'rb') as f:
            reader = csv.DictReader(f)
            total = 0
            success = 0
            for entry in reader:
                total += 1
                stepic_id = int(entry['user_id'])
                stepic_points = int(ceil(float(entry['total'])))
                try:
                    user = CSCUser.objects.get(stepic_id=stepic_id)
                except ObjectDoesNotExist:
                    self.stdout.write("No user with Stepic ID {}"
                                      .format(stepic_id))
                    continue
                try:
                    a_s = (AssignmentStudent.objects
                           .get(assignment=a, student=user))
                except ObjectDoesNotExist:
                    self.stdout.write("User ID {} with stepic ID {} doesn't "
                                      "have an assignment {}"
                                      .format(user.pk, stepic_id, a.pk))
                    continue
                a_s.grade = stepic_points
                a_s.save()
                success += 1
                self.stdout.write("Wrote {} points for user {} "
                                  "on assignment {}"
                                  .format(stepic_points, user.pk, a.pk))
            self.stdout.write("{}/{} successes".format(success, total))
