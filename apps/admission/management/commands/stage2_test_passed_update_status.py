from decimal import Decimal

from django.core.management.base import BaseCommand

from admission.models import Applicant

from ._utils import CurrentCampaignMixin
from ...constants import ApplicantStatuses


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates status to PERMIT_TO_EXAM if applicant succeed 
    in the test: score >= passing_score
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--passing_score",
            type=Decimal,
            required=True,
            help="Applicant with score: "
                 "passing_score <= score < cheater_score will be updated to PERMIT_TO_EXAM status",
        )
        parser.add_argument(
            "--cheater_score",
            type=int,
            required=True,
            dest='cheater_score',
            help="Users with a score >= cheater_score will have CHEATER status.",
        )
        parser.add_argument(
            "--new_track",
            action="store_true",
            default=False,
            dest="new_track",
            help="Update statuses for 'new track' applicants."
        )

    def handle(self, *args, **options):
        passing_score = options['passing_score']
        cheater_score = options.get('cheater_score')
        new_track = options['new_track']
        campaigns = self.get_current_campaigns(options, branch_is_required=True)
        for campaign in campaigns:
            total_applicants = Applicant.objects.filter(campaign=campaign).count()
            msg = f"{campaign} ({total_applicants} applicants)"
            self.stdout.write(msg)
            filters = {
                "campaign": campaign,
                "online_test__score__gte": passing_score,
                "new_track": new_track,
            }
            if cheater_score is not None:
                if cheater_score <= passing_score:
                    self.stdout.write("Error: passing_score should be less than cheater_score.")
                    return
                filters['online_test__score__lt'] = cheater_score
            applicants = Applicant.objects.filter(
                **filters
            ).values(
                "pk",
                "online_test__score",
                "online_test__yandex_contest_id",
                "exam__yandex_contest_id",
                "yandex_login",
                "status",
            )
            selected = 0
            updated = 0
            for a in applicants:
                selected += 1
                if a["status"] is not None:
                    msg = f"\tApplicant {a['pk']} has status {a['status']}. Skip"
                    self.stdout.write(msg)
                    continue
                (
                    Applicant.objects.filter(pk=a["pk"]).update(
                        status=Applicant.PERMIT_TO_EXAM
                    )
                )
                updated += 1
            self.stdout.write(f"    selected: {selected}")
            self.stdout.write(f"    updated: {updated}")
        self.stdout.write("Done")
