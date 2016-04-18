# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import itertools
from django.core.management import BaseCommand, CommandError

from learning.admission.models import Applicant, Test, Exam


class Command(BaseCommand):
    help = (
        "Create empty online exam results for all applicants with "
        "predefined contest_id"

        "Later we only update existed records"
    )

    def add_arguments(self, parser):
        parser.add_argument('--campaign_id', type=int,
            dest='campaign_id',
            help='Search applicants by specified campaign id')
        parser.add_argument('--passing_score', type=int,
                            help='Create records for applicants with online_test results above this value')
        parser.add_argument('--contests', type=str,
                            help='Round robin to set one of contest_id')

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]
        passing_score = options["passing_score"]
        if not options["contests"]:
            raise CommandError("No contests ids specified")
        contests = [int(c) for c in options["contests"].split(",")]
        contests = itertools.cycle(contests)
        if not campaign_id:
            raise CommandError("Campaign ID not specified")

        if not passing_score:
            raise CommandError("Passing score not specified")

        for a in Applicant.objects.filter(campaign_id=campaign_id,
                                          online_test__score__gte=passing_score).all():
            contest_id = next(contests)
            try:
                exam = Exam.objects.get(applicant=a)
            except Exam.DoesNotExist:
                Exam.objects.create(applicant=a, yandex_contest_id=contest_id, score=0)
