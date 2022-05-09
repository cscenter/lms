from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from admission.models import Applicant

from ._utils import CurrentCampaignMixin, validate_campaign_passing_score


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates status to PERMIT_TO_EXAM if applicant succeed 
    in the test: score >= passing_score
    """

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, branch_is_required=False)

        for campaign in campaigns:
            total_applicants = Applicant.objects.filter(campaign=campaign).count()
            msg = f"{campaign} ({total_applicants} applicants)"
            self.stdout.write(msg)
            try:
                validate_campaign_passing_score(campaign)
            except ValidationError as e:
                self.stdout.write(f"{e.message} Skip")
                continue

            applicants = (Applicant.objects
                          .filter(campaign=campaign,
                                  online_test__score__gte=campaign.online_test_passing_score)
                          .values("pk",
                                  "online_test__score",
                                  "online_test__yandex_contest_id",
                                  "exam__yandex_contest_id",
                                  "yandex_login",
                                  "status"))
            selected = 0
            updated = 0
            for a in applicants:
                selected += 1
                if a["status"] is not None:
                    msg = f"\tApplicant {a['pk']} has status {a['status']}. Skip"
                    self.stdout.write(msg)
                    continue
                (Applicant.objects
                 .filter(pk=a["pk"])
                 .update(status=Applicant.PERMIT_TO_EXAM))
                updated += 1
            self.stdout.write(f"    selected: {selected}")
            self.stdout.write(f"    updated: {updated}")
        self.stdout.write("Done")
