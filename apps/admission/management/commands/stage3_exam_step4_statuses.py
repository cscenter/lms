from decimal import Decimal

from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from admission.models import Applicant

from ._utils import CurrentCampaignMixin


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Updates applicant status based on exam result:
        INTERVIEW_TOBE_SCHEDULED - exam score >= Campaign.exam_score_pass
        REJECTED_BY_EXAM - exam score <= `reject_value`
        PENDING - exam score in (reject_value, exam_score_pass) range

    Assumptions:
        There is no applicants in PENDING state from the previous stages or without status at all
        If applicant omitted the exam set new status to REJECTED_BY_EXAM (not THEY_REFUSED)
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--reject_value",
            type=Decimal,
            help="Set `rejected by exam` to applicants with exam score equal or below this value.",
        )
        parser.add_argument(
            "--passing_score",
            type=Decimal,
            help="Applicant with score: "
                 "passing_score <= score < cheater_score will be updated to INTERVIEW_TOBE_SCHEDULED status",
            dest='passing_score',
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
        passing_score = options.get('passing_score')
        cheater_score = options['cheater_score']
        commit = options['commit']
        campaigns = self.get_current_campaigns(
            options, branch_is_required=True, confirm=False
        )
        assert len(campaigns) == 1
        campaign = campaigns[0]

        applicants = Applicant.objects.filter(campaign=campaign.pk)

        self.stdout.write("Минимальный шаг оценки - 0.01")
        without_status_total = applicants.filter(status__isnull=True).count()
        self.stdout.write(f"Applicants without status: {without_status_total}")
        in_pending_state_total = applicants.filter(status=Applicant.PENDING).count()
        self.stdout.write(
            f"There are {in_pending_state_total} applicants with PENDING status."
        )

        passing_score = passing_score or campaign.exam_passing_score
        if not passing_score:
            raise CommandError(f"Set exam passing score for {campaign} or provide --passing_score")
        exam_score_pass = Decimal(passing_score)
        self.stdout.write(f"{exam_score_pass} и больше - прошёл на собеседование.")

        reject_value = options["reject_value"]
        if not reject_value:
            reject_value = exam_score_pass - Decimal("0.01")
        else:
            if reject_value >= exam_score_pass:
                raise CommandError(
                    f"reject_value is greater than current "
                    f"Campaign.exam_score_pass value"
                )
            self.stdout.write(
                f"От {reject_value} до {exam_score_pass} (не "
                f"включая крайние значения) - в ожидании решения."
            )

        if (
            input(
                f"{reject_value} и меньше - отказ по результатам экзамена. "
                f"Продолжить? [y/n] "
            )
            != "y"
        ):
            self.stdout.write("Aborted")
            return

        self.stdout.write("Total applicants: {}".format(applicants.count()))

        cheaters_test = applicants.filter(
            status=Applicant.REJECTED_BY_CHEATING
        ).count()

        # Do not include cheaters here
        rejects_by_test_total = applicants.filter(
            status=Applicant.REJECTED_BY_TEST
        ).count()

        with transaction.atomic():
            rejects_by_exam_total = (
                applicants.filter(
                    Q(exam__score__lte=reject_value) | Q(exam__score__isnull=True)
                )
                .filter(
                    status__in=[
                        Applicant.PENDING,
                        Applicant.PERMIT_TO_EXAM,
                        Applicant.REJECTED_BY_EXAM,
                    ]
                )
                .exclude(exam__score__gte=cheater_score)
                .update(status=Applicant.REJECTED_BY_EXAM)
            )

            applicants.filter(
                exam__score__gte=exam_score_pass,
                exam__score__lt=cheater_score,
                status__in=[
                    Applicant.PENDING,
                    Applicant.PERMIT_TO_EXAM,
                    Applicant.INTERVIEW_TOBE_SCHEDULED,
                ],
            ).update(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
            exam_cheaters_total = applicants.filter(
                exam__score__gte=cheater_score,
                status__in=[
                    Applicant.PENDING,
                    Applicant.PERMIT_TO_EXAM,
                    Applicant.INTERVIEW_TOBE_SCHEDULED,
                ],
            ).update(status=Applicant.REJECTED_BY_EXAM_CHEATING)
            # Some applicants could have exam score < passing score, but they
            # still pass to the next stage (by manual application form check)
            # Also count those who passed the interview phase and waiting
            # for the final decision
            pass_exam_total = applicants.filter(
                status__in=[
                    Applicant.INTERVIEW_TOBE_SCHEDULED,
                    Applicant.INTERVIEW_SCHEDULED,
                    Applicant.INTERVIEW_COMPLETED,
                    Applicant.REJECTED_BY_INTERVIEW,
                ]
            ).count()

            pending_total = (
                applicants.filter(
                    exam__score__gt=reject_value,
                    exam__score__lt=exam_score_pass,
                )
                .filter(status__in=[Applicant.PERMIT_TO_EXAM, Applicant.PENDING])
                .update(status=Applicant.PENDING)
            )

            # Applicants who skipped the exam could be resolved
            # with THEY_REFUSED or REJECTED_BY_EXAM status
            refused_total = applicants.filter(status=Applicant.THEY_REFUSED).count()

            total = (
                cheaters_test,
                rejects_by_test_total,
                rejects_by_exam_total,
                exam_cheaters_total,
                pass_exam_total,
                pending_total,
                refused_total,
            )

            self.stdout.write("Cheaters test: {}".format(cheaters_test))
            self.stdout.write("Rejected by test: {}".format(rejects_by_test_total))
            self.stdout.write("Rejected by exam: {}".format(rejects_by_exam_total))
            self.stdout.write("Rejected by exam cheating: {}".format(exam_cheaters_total))
            self.stdout.write("Pass exam stage: {}".format(pass_exam_total))
            self.stdout.write("Pending status: {}".format(pending_total))
            self.stdout.write("Refused status: {}".format(refused_total))
            self.stdout.write(
                "{exp} = {result}".format(
                    exp=" + ".join((str(t) for t in total)), result=sum(total)
                )
            )
            if not commit:
                raise CommandError("Use --commit to apply changes.")
