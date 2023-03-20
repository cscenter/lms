from django.core.management.base import BaseCommand
from django.db.models import Q

from admission.models import Applicant

from ._utils import CurrentCampaignMixin


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates status to REJECTED_BY_TEST if applicant failed 
    the test: score < passing_score
    """

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, branch_is_required=False)
        for campaign in campaigns:
            total_applicants = Applicant.objects.filter(campaign=campaign).count()
            msg = f"{campaign} ({total_applicants} applicants)"
            self.stdout.write(msg)
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write(
                    f"Passing score for campaign '{campaign}' must be non zero. Skip"
                )
                continue

            applicants = (
                Applicant.objects.filter(campaign_id=campaign.pk)
                .filter(
                    Q(online_test__score__lt=testing_passing_score)
                    | Q(online_test__score__isnull=True)
                )
                .values(
                    "pk",
                    "online_test__score",
                    "online_test__yandex_contest_id",
                    "yandex_login",
                    "status",
                )
            )
            total, updated = 0, 0
            for a in applicants:
                total += 1
                if a["status"] is not None:
                    msg = f"\tApplicant {a['pk']} has status {a['status']}. Skip"
                    self.stdout.write(msg)
                    continue
                score = (
                    0
                    if a["online_test__score"] is None
                    else int(a["online_test__score"])
                )
                assert score < testing_passing_score
                (
                    Applicant.objects.filter(pk=a["pk"]).update(
                        status=Applicant.REJECTED_BY_TEST
                    )
                )
                updated += 1
            self.stdout.write(f"    total: {total}")
            self.stdout.write(f"    updated: {updated}")
        self.stdout.write("Done")
