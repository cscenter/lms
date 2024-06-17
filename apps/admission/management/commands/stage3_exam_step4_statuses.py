from decimal import Decimal

from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from admission.models import Applicant

from ._utils import CurrentCampaignMixin
from ...constants import ApplicantStatuses


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates applicant status based on exam result:
        PASSED_EXAM - exam score >= 'passing_score'
        REJECTED_BY_EXAM - exam score < 'passing_score'
        REJECTED_BY_EXAM_CHEATING - exam score >= 'cheater_score'

    Assumptions:
        All applicants with exam score have status in [PERMIT_TO_EXAM, FAILED_OLYMPIAD, ACCEPT_PAID].
        ACCEPT_PAID means postponed exam.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--passing_score",
            type=Decimal,
            required=True,
            help="Applicant with score: "
                 "passing_score <= score < cheater_score will be updated to PASSED_EXAM status",
            dest='passing_score',
        )
        parser.add_argument(
            "--new_track",
            action="store_true",
            default=False,
            dest="new_track",
            help="Update statuses for 'new track' applicants."
        )
        parser.add_argument(
            "--cheater_score",
            type=Decimal,
            required=True,
            dest='cheater_score',
            help="Users with a score >= cheater_score will have CHEATER status.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            dest="commit",
            help="Commit changes to database."
        )

    def handle(self, *args, **options):
        passing_score = options['passing_score']
        cheater_score = options['cheater_score']
        new_track = options['new_track']
        commit = options['commit']
        campaigns = self.get_current_campaigns(
            options, branch_is_required=True, confirm=False
        )
        assert len(campaigns) == 1
        campaign = campaigns[0]

        filters = {
            "campaign": campaign,
            "status__in": [ApplicantStatuses.PERMIT_TO_EXAM, ApplicantStatuses.FAILED_OLYMPIAD, ApplicantStatuses.ACCEPT_PAID],
            "new_track": new_track,
        }
        applicants = Applicant.objects.filter(**filters)
        assert all(applicant.get_exam_record() is not None for applicant in applicants)

        passing_score = Decimal(passing_score)
        self.stdout.write(f"{passing_score} и больше - прошёл экзамен.")

        if (
            input(
                f"Меньше {passing_score} - отказ по результатам экзамена. "
                f"Продолжить? [y/n] "
            )
            != "y"
        ):
            self.stdout.write("Aborted")
            return

        self.stdout.write("Total applicants: {}".format(applicants.count()))

        with transaction.atomic():
            rejects_by_exam_total = (
                applicants.filter(
                    Q(exam__score__lt=passing_score) | Q(exam__score__isnull=True)
                ).exclude(exam__score__gte=cheater_score)
                .update(status=ApplicantStatuses.REJECTED_BY_EXAM)
            )

            passed_exam_total = (
                applicants.filter(
                    exam__score__gte=passing_score,
                    exam__score__lt=cheater_score
                ).update(status=ApplicantStatuses.PASSED_EXAM))

            exam_cheaters_total = applicants.filter(
                exam__score__gte=cheater_score
            ).update(status=ApplicantStatuses.REJECTED_BY_EXAM_CHEATING)

            pass_exam_total = applicants.filter(
                status__in=ApplicantStatuses.RIGHT_BEFORE_INTERVIEW
            ).count()

            self.stdout.write(f"Rejected by exam: {rejects_by_exam_total}")
            self.stdout.write(f"Rejected by exam cheating: {exam_cheaters_total}")
            self.stdout.write(f"Passed exam: {passed_exam_total}")
            self.stdout.write("Pass exam stage: {}".format(pass_exam_total))
            if not commit:
                raise CommandError("Use --commit to apply changes.")
