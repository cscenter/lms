# -*- coding: utf-8 -*-
from enum import Enum

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import EmailTemplate, Email
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin
from learning.admission.models import Campaign, Applicant


class NotificationType(Enum):
    OPEN_DAY_PREV_YEAR = 'open-day-prev'
    OPEN_DAY_CURRENT_YEAR = 'open-day-current'

    def __str__(self):
        return self.value


class Command(CurrentCampaignsMixin, BaseCommand):
    help = """For each current campaign generates bunch of notifications"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')

    @staticmethod
    def get_template_name(campaign, type):
        return "admission-{}-{}-stage1-{}".format(campaign.year,
                                                  campaign.city.code,
                                                  type)

    def handle(self, *args, **options):
        city_code = options["city"]
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        for campaign in campaigns:
            # Check templates are exist before send any email
            for type_ in NotificationType:
                name = self.get_template_name(campaign, type_)
                if not EmailTemplate.objects.filter(name=name).exists():
                    raise CommandError(f"Abort. To continue create email "
                                       f"template with name {name}")
            self.stdout.write(f"Process campaign {campaign}")
            self._prev_campaign(campaign)
            self._current_campaign(campaign)

    def _prev_campaign(self, campaign):
        """
        Those who didn't pass previous admission campaign and didn't apply
        for the current, has possibility to submit an application
        form until deadline and visit open day.
        """
        prev_campaign = (Campaign.objects
                         .filter(city_id=campaign.city_id,
                                 year__lt=campaign.year)
                         .order_by("-year")
                         .first())
        if not prev_campaign:
            self.stdout.write(f"No previous campaign for {campaign}. Skip")
            return

        type_ = NotificationType.OPEN_DAY_PREV_YEAR
        template_name = self.get_template_name(campaign, type_)
        template = get_email_template(template_name)
        # Don't notify applicants with these statuses
        EXCLUDE_STATUSES = [Applicant.ACCEPT,
                            Applicant.ACCEPT_IF,
                            Applicant.VOLUNTEER]
        failed_in_prev_campaign = (Applicant.subscribed
                                   .filter(campaign_id=prev_campaign.pk)
                                   .exclude(status__in=EXCLUDE_STATUSES,
                                            user__isnull=False)
                                   .values_list('email', flat=True))
        sent = 0
        already_submitted = 0
        for email in failed_in_prev_campaign:
            current_campaign_participant = Applicant.objects.filter(
                campaign_id=campaign.pk, email=email)
            if not current_campaign_participant.exists():
                recipients = [email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender='CS центр <info@compscicenter.ru>',
                        template=template_name,
                        # Render on delivery, we have no really big
                        # amount of emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
                    sent += 1
            else:
                already_submitted += 1
        self.stdout.write(f"Emails generated {sent} [{type_}]. "
                          f"Who submitted: {already_submitted}")

    def _current_campaign(self, campaign):
        """Generates notification about open day for those who submitted an
        application form."""
        type_ = NotificationType.OPEN_DAY_CURRENT_YEAR
        template_name = self.get_template_name(campaign, type_)
        template = get_email_template(template_name)
        applicants = Applicant.subscribed.filter(campaign_id=campaign.pk)
        sent = 0
        for applicant in applicants:
            recipients = [applicant.email]
            if not Email.objects.filter(to=recipients,
                                        template=template).exists():
                mail.send(
                    recipients,
                    sender='CS центр <info@compscicenter.ru>',
                    template=template_name,
                    # Render on delivery, we have no really big
                    # amount of emails to think about saving CPU time
                    render_on_delivery=True,
                    backend='ses',
                )
                sent += 1
        self.stdout.write(f"Emails generated {sent} [{type_}].")
