# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from admission.models import Applicant, Exam, Contest, ChallengeStatuses
from api.providers.yandex_contest import YandexContestAPI, \
    YandexContestAPIException, RegisterStatus
from ._utils import CurrentCampaignsMixin


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """
    For those who passed testing (score >= passing_score) creates 
    exam record and registers in yandex contest. 
    XXX: This command doesn't set new status to the applicant model.
    """

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
            self.stdout.write(f"Processing {campaign}:")
            passing_score = campaign.online_test_passing_score
            if not passing_score:
                self.stdout.write("Zero passing score. Skip campaign")
                continue
            # Make sure we already have associated with campaign exam contests
            if not Contest.objects.filter(type=Contest.TYPE_EXAM,
                                          campaign=campaign).exists():
                self.stdout.write(f"No exam contests found for `{campaign}`. "
                                  f"Skip campaign processing.")
                continue

            api = YandexContestAPI(access_token=campaign.access_token,
                                   refresh_token=campaign.refresh_token)

            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk,
                                  online_test__score__gte=passing_score))
            for a in applicants:
                exam, _ = Exam.objects.get_or_create(
                    applicant=a,
                    defaults={"status": ChallengeStatuses.NEW})
                try:
                    exam.register_in_contest(api, a)
                except YandexContestAPIException as e:
                    error_status_code, text = e.args
                    if error_status_code == RegisterStatus.BAD_TOKEN:
                        self.stdout.write(f"Bad Token for campaign {campaign}")
                        break
                    self.stdout.write(
                        f"API request error for applicant {a}. "
                        f"Code: {error_status_code}. Message: {text}"
                    )
                    continue
        self.stdout.write("Done")
