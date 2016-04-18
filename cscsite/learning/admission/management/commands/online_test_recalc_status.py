# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand, CommandError
from django.db.models import Q

from learning.admission.models import Applicant, Test


class Command(BaseCommand):
    help = (
        "Recalculate applicant statuses based on online test passing score. "

        "Has an effect only if applicant status not selected or "
        "set to `rejected_by_test`."
    )

    def add_arguments(self, parser):
        parser.add_argument('--campaign_id', type=int,
            dest='campaign_id',
            help='Filter online test results by campaign')

        parser.add_argument('--passing_score', type=int,
            help='Set `rejected by online test` '
                 'status for applicants below passing score')

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]
        if not campaign_id:
            raise CommandError("Campaign ID not specified")
        passing_score = options["passing_score"]
        if not passing_score:
            raise CommandError("Passing score not specified")

        q = (Test.objects
             .filter(Q(applicant__status__isnull=True) | Q(applicant__status=Applicant.REJECTED_BY_TEST),
                     score__lt=passing_score,
                     applicant__campaign=campaign_id)
             .select_related("applicant"))
        # TODO: write test1 - recalc applicant status only from selected campaign
        # TODO: write test2 - we are not change status if it's set and not equal REJECTED_BY_TEST
        for online_test in q:
            online_test.applicant.status = Applicant.REJECTED_BY_TEST
            online_test.applicant.save()


