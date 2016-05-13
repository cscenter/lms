# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from datetime import datetime

from django.core.management import BaseCommand, CommandError

import unicodecsv as csv

from learning.admission.models import Applicant, Test, Interview, Comment


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            'csv', metavar='CSV',
            help='path to csv with data')

    def handle(self, *args, **options):
        with open(options['csv'], 'rb') as f:
            reader = csv.DictReader(f, encoding='utf-8')
            # reader.unicode_fieldnames
            for row in reader:
                stepic_id = row["stepic_id"]
                try:
                    applicant = Applicant.objects.get(stepic_id=stepic_id, campaign=1)
                except Applicant.DoesNotExist:
                    continue
                # format date
                d, rest = row["created"].strip().split(".", 1)
                if len(d) == 1:
                    d = "0" + d
                created = d + "." + rest
                created = datetime.strptime(created, '%d.%m.%Y %H:%M')
                # get interviewers
                interviewers = {}
                for k, v in row.items():
                    if k not in ["status", "stepic_id", "created", "text"] and v:
                        try:
                            score = int(v)
                            if score > 2 or score < -2:
                                print("bad score")
                                continue
                        except ValueError:
                            print("bad score")
                            continue
                        try:
                            interviewers[k] = score
                        except ValueError:
                            print("cant cast column id to interviewer_id")
                interview = Interview(status=Interview.COMPLETED,
                                      date=created,
                                      applicant=applicant)
                interview.save()
                # save applicant to override status
                if "берём" in row["status"]:
                    applicant.status = Applicant.ACCEPT
                elif "вольнослушатель" in row["status"]:
                    applicant.status = Applicant.VOLUNTEER
                elif "отказ" in row["status"]:
                    applicant.status = Applicant.REJECTED_BY_INTERVIEW
                applicant.save()
                ids = [int(id) for id in interviewers.keys()]
                interview.interviewers.add(*ids)
                # create comments
                for id, score in interviewers.items():
                    id = int(id)
                    comment = Comment(score=score, interview=interview, interviewer_id=id)
                    if id == 38: # Katya account - 38
                        comment.text = row["text"]
                    comment.save()
                if "38" not in interviewers:
                    print(comment.pk)
                    comment.text = row["text"]
                    comment.save()


