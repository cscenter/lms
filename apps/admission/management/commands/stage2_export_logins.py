# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from admission.models import Applicant
from ._utils import CurrentCampaignMixin


class Command(CurrentCampaignMixin, BaseCommand):
    help = """Prints list of yandex ids who successfully passed test"""

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
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
                          .values("id", "yandex_login",
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
                self.stdout.write(a["yandex_login"])
            self.stdout.write("")
        self.stdout.write("Done")
