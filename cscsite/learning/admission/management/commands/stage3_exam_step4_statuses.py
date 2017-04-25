# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand, CommandError
from django.db.models import Q

from ._utils import CurrentCampaignsMixin
from learning.admission.models import Applicant, Test


# FIXME: Сейчас явно установлены статусы "Отказ по результатам теста" и "Допущен к экзамену".
# FIXME: Имеет смысл явно использовать эти статусы перед выборкой? Можно сверять размер выборки и находить проблемных таким образом
class Command(CurrentCampaignsMixin, BaseCommand):
    help = (
        "Recalculate applicant statuses for selected campaign."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')
        parser.add_argument(
            '--exam_score_reject', type=int,
            help='Set `rejected by exam` for applicants with exam score'
                 ' below this value')

    def handle(self, *args, **options):
        """
        1. Set status `REJECTED_BY_TEST` for applicants without online
        exam record
        2. Set `REJECTED_BY_EXAM` for applicants with exam score below
        `exam_score_reject` value
        3. Set `INTERVIEW_TOBE_SCHEDULED` for applicants with exam score above
        `exam_score_pass` value
        4. Set `PENDING` for applicants with exam score
        in [exam_score_reject;exam_score_pass]
        """

        if not options["city"]:
            raise CommandError("Provide city code for current campaign")
        city_code = options["city"]
        campaigns = self.get_current_campaigns(city_code)
        assert len(campaigns) > 1
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return
        campaign = campaigns.pop()
        exam_score_reject = options["exam_score_reject"]
        if not exam_score_reject:
            raise CommandError("Exam score value for rejection not specified")
        exam_score_pass = campaign.exam_passing_score
        if not exam_score_pass:
            self.stdout.write("Zero exam passing score "
                              "for {}. Cancel".format(campaign))
            return

        print("Total applicants: {}".format(
            Applicant.objects.filter(campaign=campaign.pk).count()))

        print("Cheaters: {}".format(Applicant.objects
                .filter(campaign=campaign.pk,
                        status=Applicant.REJECTED_BY_CHEATING).count()))

        rejects_by_test_q = (Applicant.objects
                             .filter(campaign=campaign.pk,
                                     exam__isnull=True))
        print("Rejected by test: {}".format(rejects_by_test_q.count()))
        rejects_by_test_q.update(status=Applicant.REJECTED_BY_TEST)

        rejects_by_exam_q = (Applicant.objects
                             .filter(campaign=campaign.pk,
                                     exam__score__lt=exam_score_reject)
                             .filter(Q(status__isnull=True) |
                                     Q(status=Applicant.PENDING) |
                                     Q(status=Applicant.REJECTED_BY_EXAM)))
        print("Rejected by exam: {}".format(rejects_by_exam_q.count()))
        rejects_by_exam_q.update(status=Applicant.REJECTED_BY_EXAM)
        # FIXME: passing_score - inclusive or exclusive???
        pass_exam_q = (Applicant.objects
                       .filter(campaign=campaign.pk,
                               exam__score__gt=exam_score_pass)
                       .filter(Q(status__isnull=True) |
                               Q(status=Applicant.PENDING) |
                               Q(status=Applicant.INTERVIEW_TOBE_SCHEDULED)))
        print("Pass exam: {}".format(pass_exam_q.count()))
        pass_exam_q.update(status=Applicant.INTERVIEW_TOBE_SCHEDULED)

        pending_q = (Applicant.objects
                       .filter(campaign=campaign.pk,
                               exam__score__gte=exam_score_reject,
                               exam__score__lte=exam_score_pass)
                       .filter(Q(status__isnull=True) |
                               Q(status=Applicant.PENDING)))
        print("Pending status: {}".format(pending_q.count()))
        pending_q.update(status=Applicant.PENDING)
