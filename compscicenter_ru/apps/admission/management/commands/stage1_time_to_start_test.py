# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin
from admission.models import Applicant, Test


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    TEMPLATE_TYPE = "testing-reminder"
    help = """
    Send notification to those who applied but haven't yet started the contest.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')

    def handle(self, *args, **options):
        city_code = options["city"]
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        self.validate_templates(campaigns, types=[self.TEMPLATE_TYPE])

        generated = 0
        for campaign in campaigns:
            template_name = self.get_template_name(campaign, self.TEMPLATE_TYPE)
            template = get_email_template(template_name)
            tests = (Test.objects
                     .filter(applicant__campaign_id=campaign.pk,
                             score__isnull=True,
                             status=Test.REGISTERED)
                     .values("applicant__email",
                             "yandex_contest_id"))

            for t in tests.iterator():
                email = t["applicant__email"]
                mail.send(
                    [email],
                    sender='CS центр <info@compscicenter.ru>',
                    template=template,
                    context={
                      "CONTEST_ID": t["yandex_contest_id"]
                    },
                    render_on_delivery=True,
                    backend='ses',
                )
                generated += 1
        self.stdout.write("Generated emails: {}".format(generated))
        self.stdout.write("Done")
