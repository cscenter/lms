# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import EmailTemplate, Email
from post_office.utils import get_email_template

from learning.admission.management.commands._utils import CurrentCampaignsMixin
from learning.admission.models import Campaign, Applicant




class Command(CurrentCampaignsMixin, BaseCommand):
    help = """
    For selected campaign generate emails about admission results
    based on interview results.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')

    @staticmethod
    def get_template_name(campaign, status):
        return "admission-{}-{}-interview-{}".format(campaign.year,
                                                     campaign.city.code,
                                                     status)

    def handle(self, *args, **options):
        city_code = options["city"]
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        for campaign in campaigns:
            # Check templates exists before send any email
            for status in Applicant.FINAL_STATUSES:
                template_name = self.get_template_name(campaign, status)
                if not EmailTemplate.objects.filter(name=template_name).exists():
                    raise CommandError(
                        "Abort. To continue create "
                        "email template with name {}".format(template_name))
            context = {
                'SUBJECT_CITY': campaign.city.name
            }
            # Generate emails for each status
            for status in Applicant.FINAL_STATUSES:
                template_name = self.get_template_name(campaign, status)
                template = get_email_template(template_name)
                applicants = Applicant.objects.filter(campaign_id=campaign.pk,
                                                      status=status)
                sent = 0
                for a in applicants:
                    if a.status in Applicant.FINAL_STATUSES:
                        recipients = [a.email]
                        if not Email.objects.filter(to=recipients,
                                                    template=template).exists():
                            mail.send(
                                recipients,
                                sender='info@compscicenter.ru',
                                template=template_name,
                                context=context,
                                # Render on delivery, we have no really big
                                # amount of emails to think about saving CPU time
                                render_on_delivery=True,
                                backend='ses',
                            )
                            sent += 1
                print("for status {} {} emails generated.".format(status, sent))



