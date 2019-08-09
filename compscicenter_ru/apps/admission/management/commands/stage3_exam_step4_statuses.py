# -*- coding: utf-8 -*-
from decimal import Decimal

from django.core.management import BaseCommand, CommandError
from django.db.models import Q

from ._utils import CurrentCampaignsMixin
from admission.models import Applicant, Test, Campaign


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """
    Updates applicant status for selected campaign based on exam results.

    Details:
        Set `INTERVIEW_TOBE_SCHEDULED` to applicants with exam score >= Campaign.exam_score_pass
        Set `REJECTED_BY_EXAM` to applicants with exam score <= `reject_value`
        Set `PENDING` to applicants with exam score in (reject_value, exam_score_pass) range
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--reject_value', type=Decimal,
            help='Set `rejected by exam` to applicants with exam score equal or'
                 ' below this value.')

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, required=True)
        assert len(campaigns) == 1
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        campaign = campaigns.get()
        self.stdout.write("Минимальный шаг оценки - 0.01")
        exam_score_pass = Decimal(campaign.exam_passing_score)
        if not exam_score_pass:
            self.stdout.write(f"Zero exam passing score for {campaign}. Cancel")
            return
        self.stdout.write(f"{exam_score_pass} и больше - прошёл на собеседование.")

        reject_value = options["reject_value"]
        if not reject_value:
            reject_value = exam_score_pass - Decimal('0.01')
        else:
            if reject_value >= exam_score_pass:
                raise CommandError(f"reject_value is greater than current "
                                   f"Campaign.exam_score_pass value")
            self.stdout.write(f"От {reject_value} до {exam_score_pass} (не "
                              f"включая крайние значения) - в ожидании решения.")

        if input(f"{reject_value} и меньше - отказ по результатам экзамена. "
                 f"Продолжить? [y/n] ") != "y":
            self.stdout.write("Aborted")
            return

        self.stdout.write("Total applicants: {}".format(
            Applicant.objects.filter(campaign=campaign.pk).count()))

        total_cheaters = (Applicant.objects
                          .filter(campaign=campaign.pk,
                                  status=Applicant.REJECTED_BY_CHEATING)
                          .count())

        total_rejected_by_test = (Applicant.objects
                                  .filter(campaign=campaign.pk,
                                          status=Applicant.REJECTED_BY_TEST)
                                  .count())

        rejects_by_exam_q = (Applicant.objects
                             .filter(campaign=campaign.pk)
                             .filter(Q(exam__score__lte=reject_value) |
                                     Q(exam__score__isnull=True))
                             .filter(Q(status__isnull=True) |
                                     Q(status=Applicant.PENDING) |
                                     Q(status=Applicant.PERMIT_TO_EXAM) |
                                     Q(status=Applicant.REJECTED_BY_EXAM)))
        total_rejects_by_exam = rejects_by_exam_q.update(
            status=Applicant.REJECTED_BY_EXAM)

        pass_exam_q = (Applicant.objects
                       .filter(campaign=campaign.pk,
                               exam__score__gte=exam_score_pass)
                       .filter(Q(status__isnull=True) |
                               Q(status=Applicant.PENDING) |
                               Q(status=Applicant.PERMIT_TO_EXAM) |
                               Q(status=Applicant.INTERVIEW_TOBE_SCHEDULED)))
        total_pass_exam = pass_exam_q.update(
            status=Applicant.INTERVIEW_TOBE_SCHEDULED)
        # Some applicants could have exam score < passing score, but they
        # still pass to the next stage (by manual application form check)
        # Also count those who passed the interview phase and waiting
        # for the final decision
        interviewed = (Applicant.objects
                       .filter(campaign=campaign.pk)
                       .filter(Q(status=Applicant.INTERVIEW_TOBE_SCHEDULED) |
                               Q(status=Applicant.INTERVIEW_SCHEDULED) |
                               Q(status=Applicant.INTERVIEW_COMPLETED) |
                               Q(status=Applicant.REJECTED_BY_INTERVIEW))
                       .count())
        total_pass_exam = interviewed

        pending_q = (Applicant.objects
                     .filter(campaign=campaign.pk,
                             exam__score__gt=reject_value,
                             exam__score__lt=exam_score_pass)
                     .filter(Q(status__isnull=True) |
                             Q(status=Applicant.PERMIT_TO_EXAM) |
                             Q(status=Applicant.PENDING)))
        total_pending = pending_q.update(status=Applicant.PENDING)

        # If the applicant skipped the exam, he also becomes refused
        refused_qs = (Applicant.objects
                      .filter(campaign=campaign.pk,
                              status=Applicant.THEY_REFUSED))
        total_refused = refused_qs.count()

        total_all = (
            total_cheaters,
            total_rejected_by_test,
            total_rejects_by_exam,
            total_pass_exam,
            total_pending,
            total_refused
        )

        self.stdout.write("Cheaters: {}".format(total_cheaters))
        self.stdout.write("Rejected by test: {}".format(total_rejected_by_test))
        self.stdout.write("Rejected by exam: {}".format(total_rejects_by_exam))
        self.stdout.write("Pass exam stage: {}".format(total_pass_exam))
        self.stdout.write("Pending status: {}".format(total_pending))
        self.stdout.write("Refused status: {}".format(total_refused))
        self.stdout.write("{} = {}".format(
            " + ".join((str(t) for t in total_all)),
            sum(total_all)
        ))
