# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.utils import get_email_template

from ._utils import ValidateTemplatesMixin, CurrentCampaignsMixin
from admission.models import Applicant, Exam


# TODO: Make `city` attr required
class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    TEMPLATE_TYPE = "exam-contest"
    help = 'Generate mails about contest check completeness'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')

    def handle(self, *args, **options):
        city_code = options["city"] if options["city"] else None
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        self.validate_templates(campaigns, types=[self.TEMPLATE_TYPE])

        generated = 0
        for campaign in campaigns:
            template_name = self.get_template_name(campaign, self.TEMPLATE_TYPE)
            template = get_email_template(template_name)
            exam_results = (
                Exam.objects
                # Note: Django generates query like filter rows with
                # status != 'reject_cheating' or with NULL status
                .filter(applicant__campaign=campaign.pk)
                .exclude(applicant__status=Applicant.REJECTED_BY_CHEATING)
                .select_related("applicant")
            )
            print(exam_results.query)

            for e in exam_results:
                applicant = e.applicant
                mail.send(
                    [applicant.email],
                    sender='info@compscicenter.ru',
                    template=template,
                    # Render on delivery, we have no really big amount of
                    # emails to think about saving CPU time
                    render_on_delivery=True,
                    backend='ses',
                )
                generated += 1
        self.stdout.write("Generated emails: {}".format(generated))
        self.stdout.write("Done")


