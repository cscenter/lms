# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand, CommandError

from learning.admission.models import Applicant, Test


class Command(BaseCommand):
    help = (
        "Create empty online test results for all applicants."

        "Later we want send reject email even they are not specified correct "
        "yandex login, but has access to contest. It may happens when "
        "user filled application under authorized yandex account, "
        "but made mistake on filling out yandex id field"
    )

    def add_arguments(self, parser):
        parser.add_argument('--campaign_id', type=int,
            dest='campaign_id',
            help='Search applicants by specified campaign id')

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]
        if not campaign_id:
            raise CommandError("Campaign ID not specified")

        for a in Applicant.objects.filter(campaign_id=campaign_id).all():
            try:
                online_test = Test.objects.get(applicant=a)
            except Test.DoesNotExist:
                Test.objects.create(applicant=a, score=0)
