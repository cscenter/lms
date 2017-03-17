# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import itertools
from django.core.management import BaseCommand, CommandError

from ._utils import CurrentCampaignsMixin
from learning.admission.models import Applicant, Test, Exam


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """
        Create empty exam results record (if not exists) for each applicant 
        who successfully passed test (score >= test passing score). 
        Randomly set contest id.
        """

    def add_arguments(self, parser):
        parser.add_argument(
            '--contests', type=str,
            help='Comma separated contest ids')

    # TODO: Get contest_id from DB by yandex contest id value after replacing yandex_contest_id with FK
    def handle(self, *args, **options):
        if not options["contests"]:
            raise CommandError("Specify contests ids")
        contests = [int(c) for c in options["contests"].split(",")]
        contests = itertools.cycle(contests)

        campaigns = self.get_current_campaigns()
        for campaign in campaigns:
            passing_score = campaign.online_test_passing_score
            if not passing_score:
                self.stdout.write("Zero passing score "
                                  "for {}. Skip".format(campaign))
                continue

            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk,
                                  online_test__score__gte=passing_score)
                          .all())
            for a in applicants:
                self.stdout.write(a.yandex_id)
                contest_id = next(contests)
                try:
                    _ = Exam.objects.get(applicant=a)
                except Exam.DoesNotExist:
                    Exam.objects.create(applicant=a,
                                        yandex_contest_id=contest_id,
                                        score=0)
        self.stdout.write("Done")
