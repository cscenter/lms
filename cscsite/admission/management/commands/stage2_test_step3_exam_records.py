# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import itertools
from django.core.management import BaseCommand, CommandError

from ._utils import CurrentCampaignsMixin
from admission.models import Applicant, Test, Exam, Contest


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """
        Deprecated. Creates empty exam results record (if not exists) for 
        each applicant who successfully passed test (score >= test passing 
        score). 
        Randomly set contest id.
        """

    def add_arguments(self, parser):
        parser.add_argument(
            '--contests', type=str,
            help='Comma separated contest ids')

    # TODO: Get contest_id from DB by yandex contest id value
    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns()
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return
        for campaign in campaigns:
            passing_score = int(campaign.online_test_passing_score)
            if not passing_score:
                self.stdout.write("Zero passing score "
                                  "for {}. Skip".format(campaign))
                continue

            contests = (Contest.objects
                        .filter(campaign=campaign)
                        .values_list("contest_id", flat=True))
            if not contests.exists():
                self.stdout.write("Contests not provided for "
                                  "campaign {}. Skip".format(campaign))
                continue
            contests = itertools.cycle(contests)
            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk,
                                  online_test__score__gte=passing_score)
                          .values("id", "yandex_id"))
            for a in applicants:
                contest_id = next(contests)
                try:
                    _ = Exam.objects.get(applicant_id=a["id"])
                except Exam.DoesNotExist:
                    Exam.objects.create(applicant_id=a["id"],
                                        yandex_contest_id=contest_id)
        self.stdout.write("Done")
