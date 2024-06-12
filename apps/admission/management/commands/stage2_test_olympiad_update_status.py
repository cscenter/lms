from django.core.management.base import BaseCommand

from admission.models import Applicant

from ._utils import CurrentCampaignMixin
from ...constants import ApplicantStatuses


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates status to PERMIT_TO_OLYMPIAD if applicant performed well
    in the test: left_bound <= score <= right_bound
    Use only after stage2_test_passed_update_status usage
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--left_bound",
            type=int,
            required=True,
        )
        parser.add_argument(
            "--right_bound",
            type=int,
            required=True,
        )
        parser.add_argument(
            "--new_track",
            action="store_true",
            default=False,
            dest="new_track",
            help="Update statuses for 'new track' applicants."
        )

    def handle(self, *args, **options):
        left_bound = options.get('left_bound')
        right_bound = options.get('right_bound')
        new_track = options['new_track']
        campaigns = self.get_current_campaigns(options, branch_is_required=True)
        for campaign in campaigns:
            total_applicants = Applicant.objects.filter(campaign=campaign).count()
            msg = f"{campaign} ({total_applicants} applicants)"
            self.stdout.write(msg)
            if right_bound < left_bound:
                self.stdout.write("Error: left_bound should be <= right_bound")
                return
            filters = {
                "campaign": campaign,
                "online_test__score__gte": left_bound,
                "online_test__score__lte": right_bound,
                "new_track": new_track,
            }
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
                if a["status"] != ApplicantStatuses.PERMIT_TO_EXAM:
                    msg = f"\tApplicant {a['pk']} has status {a['status']}. Skip"
                    self.stdout.write(msg)
                    continue
                (
                    Applicant.objects.filter(pk=a["pk"]).update(
                        status=ApplicantStatuses.PERMIT_TO_OLYMPIAD
                    )
                )
                updated += 1
            self.stdout.write(f"    selected: {selected}")
            self.stdout.write(f"    updated: {updated}")
        self.stdout.write("Done")
