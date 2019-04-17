# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand, CommandError

from ._utils import CurrentCampaignsMixin
from admission.models import Applicant


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """Prints list of yandex ids who successfully passed test"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')

    def handle(self, *args, **options):
        city_code = options["city"]
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        for campaign in campaigns:
            self.stdout.write(f"Processing {campaign}")
            passing_score = campaign.online_test_passing_score
            if not passing_score:
                self.stdout.write("Zero passing score. Skip campaign")
                continue

            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk,
                                  online_test__score__gte=passing_score)
                          .values("id", "yandex_id",
                                  "exam__yandex_contest_id")
                          .order_by("exam__yandex_contest_id"))
            contest_id = object()
            for a in applicants:
                if not a["exam__yandex_contest_id"]:
                    self.stdout.write(f"Missing contest id for {a['id']}!. Skip")
                    continue
                if a["exam__yandex_contest_id"] != contest_id:
                    contest_id = a["exam__yandex_contest_id"]
                    self.stdout.write("CONTEST ID #{}:".format(contest_id))
                self.stdout.write(a["yandex_id"])
            self.stdout.write("")
        self.stdout.write("Done")
