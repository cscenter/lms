# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand, CommandError

from ._utils import CurrentCampaignsMixin
from learning.admission.models import Applicant, Test


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """
    Create empty record on test result (if not exists) for each applicant.

    It's necessary step, cause we want send rejection email even if student 
    made a mistake in yandex login, but has access to contest. 
    It's possible when user filled application under authorized yandex 
    account, but made mistake on filling out yandex id field.
    """

    def handle(self, *args, **options):
        campaign_ids = self.get_current_campaign_ids()
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        for campaign_id in campaign_ids:
            for a in Applicant.objects.filter(campaign_id=campaign_id).all():
                try:
                    _ = Test.objects.get(applicant=a)
                except Test.DoesNotExist:
                    Test.objects.create(applicant=a, score=0)
        self.stdout.write("Done")
