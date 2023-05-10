from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from admission.models import Applicant

from ._utils import CurrentCampaignMixin
from ...constants import ApplicantStatuses


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates status to REJECTED_BY_TEST if applicant failed 
    the test: score < passing_score
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
            default_filters = Q(online_test__score__lt=passing_score) | Q(online_test__score__isnull=True)
            if cheater_score:
                default_filters |= Q(online_test__score__gte=cheater_score)
            applicants = (
                Applicant.objects.filter(campaign_id=campaign.pk)
                .exclude(
                    # bonus from past admission campaign
                    status=ApplicantStatuses.INTERVIEW_TOBE_SCHEDULED
                )
                .filter(
                    data__new_track=new_track
                )
                .filter(
                    default_filters
                )
                .values(
                    "pk",
                    "online_test__score",
                    "online_test__yandex_contest_id",
                    "yandex_login",
                    "status",
                )
            )
            total, update_rejected, update_cheater = 0, 0, 0
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
                if score < passing_score:
                    status = Applicant.REJECTED_BY_TEST
                elif score >= cheater_score:
                    status = Applicant.REJECTED_BY_CHEATING
                else:
                    raise NotImplementedError("Something goes wrong...")
                (
                    Applicant.objects.filter(pk=a["pk"]).update(
                        status=status
                    )
                )
                if status == Applicant.REJECTED_BY_TEST:
                    update_rejected += 1
                else:
                    update_cheater += 1
            self.stdout.write(f"    total: {total}")
            self.stdout.write(f"    updated rejected: {update_rejected}")
            self.stdout.write(f"    updated cheater: {update_cheater}")
        self.stdout.write("Done")
