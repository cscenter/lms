# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from ._utils import ValidateTemplatesMixin, CurrentCampaignsMixin
from learning.admission.models import Applicant, Exam


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    TEMPLATE_REGEXP = "admission-{year}-{city_code}-exam-{type}"
    help = 'Generate emails about online exam results'

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

        self.validate_templates(campaigns)

        generated = 0
        for campaign in campaigns:
            self.stdout.write("{}:".format(campaign))
            succeed_applicants = (Applicant.objects
                                  .filter(campaign=campaign.pk,
                                          status=Applicant.INTERVIEW_TOBE_SCHEDULED)
                                  .only("email"))
            print("Succeed total: {}".format(len(succeed_applicants)))
            for applicant in succeed_applicants:
                template_name = self.get_template_name(campaign, "success")
                template = get_email_template(template_name)
                recipients = [applicant.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender='info@compscicenter.ru',
                        template=template,
                        # Render on delivery, we have no really big amount of
                        # emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
            failed_applicants = (Applicant.objects
                                 .filter(campaign=campaign.pk,
                                         status=Applicant.REJECTED_BY_EXAM)
                                 .only("email"))
            print("Failed total: {}".format(len(failed_applicants)))
            for applicant in failed_applicants:
                template_name = self.get_template_name(campaign, "fail")
                template = get_email_template(template_name)
                recipients = [applicant.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender='info@compscicenter.ru',
                        template=template,
                        # Render on delivery, we have no really big amount of
                        # emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
        self.stdout.write("Generated emails: {}".format(generated))
        self.stdout.write("Done")

