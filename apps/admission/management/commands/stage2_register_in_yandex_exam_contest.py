# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from admission.models import Applicant, Exam, Contest
from admission.constants import ChallengeStatuses
from api.providers.yandex_contest import YandexContestAPI, \
    YandexContestAPIException, RegisterStatus, ContestAPIError
from ._utils import CurrentCampaignMixin, CustomizeQueryMixin


class Command(CurrentCampaignMixin, CustomizeQueryMixin, BaseCommand):
    help = """
    For those who passed testing (score >= passing_score) creates 
    exam record and registers in yandex contest. 
    XXX: This command doesn't set new status to the applicant model.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        manager = self.get_manager(Applicant, options)

        for campaign in campaigns:
            self.stdout.write(f"Processing {campaign}:")
            passing_score = campaign.online_test_passing_score
            if not passing_score:
                self.stdout.write("Zero passing score. Skip campaign")
                continue
            # Make sure we have exam contests associated with campaign
            # Otherwise we can't assign random contest number
            if not Contest.objects.filter(type=Contest.TYPE_EXAM,
                                          campaign=campaign).exists():
                self.stdout.write(f"No exam contests found for `{campaign}`. "
                                  f"Skip campaign processing.")
                continue

            api = YandexContestAPI(access_token=campaign.access_token,
                                   refresh_token=campaign.refresh_token)

            applicants = (manager
                          .filter(campaign_id=campaign.pk,
                                  online_test__score__gte=passing_score))
            for a in applicants:
                exam, created = Exam.objects.get_or_create(
                    applicant=a,
                    defaults={"status": ChallengeStatuses.NEW})
                if created or exam.status == ChallengeStatuses.NEW:
                    try:
                        exam.register_in_contest(api)
                    except ContestAPIError as e:
                        if e.code == RegisterStatus.BAD_TOKEN:
                            self.stdout.write(f"Bad campaign token {campaign}")
                            break
                        self.stdout.write(
                            f"API request error for applicant {a}. "
                            f"Code: {e.code}. Message: {e.message}"
                        )
                        continue
        self.stdout.write("Done")
