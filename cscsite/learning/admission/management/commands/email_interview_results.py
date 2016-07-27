# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import EmailTemplate

from learning.admission.models import Campaign, Applicant


class Command(BaseCommand):
    help = """
    For selected campaign generate emails about admission results
    based on interview results.
    """

    def add_arguments(self, parser):
        # TODO: replace with campaign year, cast campaign code to unique int
        parser.add_argument('--campaign_id', type=int,
                            dest='campaign_id',
                            help='Campaign ID')

    @staticmethod
    def get_template_name(code, status):
        return "admission-{}-interview-{}".format(code, status)

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]
        if not campaign_id:
            raise CommandError("Specify campaign ID")

        try:
            admission_campaign = Campaign.objects.get(pk=campaign_id)
        except Campaign.DoesNotExist:
            raise CommandError("Admission campaign with id=%s not found"
                               % campaign_id)

        statuses = [Applicant.ACCEPT,
                    Applicant.ACCEPT_IF,
                    Applicant.REJECTED_BY_INTERVIEW,
                    Applicant.VOLUNTEER]
        # Check templates exists before send any email
        for status in statuses:
            template_name = self.get_template_name(admission_campaign.code,
                                                   status)
            if not EmailTemplate.objects.filter(name=template_name).exists():
                raise CommandError("Abort. To continue create email template "
                                   "with name {}".format(template_name))
        # Now generate emails
        for status in statuses:
            template_name = self.get_template_name(admission_campaign.code,
                                                   status)

            applicants = Applicant.objects.filter(campaign_id=campaign_id,
                                                  status=status)
            for a in applicants:
                mail.send(
                    [a.email],
                    sender='info@compscicenter.ru',
                    template=template_name,
                    backend='ses',
                )
            print("for status {} {} emails generated.".format(status,
                                                              len(applicants)))



