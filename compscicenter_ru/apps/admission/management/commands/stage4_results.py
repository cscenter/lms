# -*- coding: utf-8 -*-
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.management.commands._utils import CurrentCampaignsMixin, \
    ValidateTemplatesMixin, CustomizeQueryMixin
from admission.models import Applicant


class Command(ValidateTemplatesMixin, CustomizeQueryMixin,
              CurrentCampaignsMixin, BaseCommand):
    TEMPLATE_REGEXP = "admission-{year}-{branch_code}-results-{status}"
    help = """
    Generates emails with final decision based on applicant status.

    Example:
        ./manage.py stage4_results --branch=nsk -f="status__in=['volunteer']"
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--from', type=str,
            default='CS центр <info@compscicenter.ru>',
            help='Override default `From` header')

    def get_template_name(self, campaign, suffix):
        return self.TEMPLATE_REGEXP.format(
            year=campaign.year,
            branch_code=campaign.branch.code,
            status=suffix
        )

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, required=True)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        header_from = options["from"]

        manager = self.get_manager(Applicant, options)

        for campaign in campaigns:
            self.stdout.write("{}:".format(campaign))
            applicants = manager.filter(campaign_id=campaign.pk)

            all_statuses = applicants.values_list('status', flat=True).distinct()
            self.validate_templates(campaigns, types=all_statuses)

            stats = Counter()
            for a in applicants.order_by('status').iterator():
                template_name = self.get_template_name(campaign, a.status)
                template = get_email_template(template_name)
                recipients = [a.email]
                # Render email on delivery, it makes
                # `Email.objects.exists()` work correctly.
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender=header_from,
                        template=template,
                        render_on_delivery=True,
                        backend='ses',
                    )
                    stats[a.status] += 1
            for status, generated in stats.items():
                self.stdout.write(f"Status: {status}. Generated: {generated}")



