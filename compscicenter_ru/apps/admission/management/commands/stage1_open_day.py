# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignMixin, EmailTemplateMixin
from admission.services import get_email_from


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    TEMPLATE_REGEXP = "admission-{year}-{branch_code}-stage1-{type}"
    TEMPLATE_TYPE = 'open-day'
    help = """Generate notification about open day for those who submitted an application form."""

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        self.validate_templates(campaigns, types=[self.TEMPLATE_TYPE])

        for campaign in campaigns:
            self.stdout.write(f"Process campaign {campaign}")
            self._generate_notifications(campaign)

    def _generate_notifications(self, campaign):
        email_from = get_email_from(campaign)
        template_name = self.get_template_name(campaign, self.TEMPLATE_TYPE)
        template = get_email_template(template_name)
        applicants = Applicant.subscribed.filter(campaign_id=campaign.pk)
        sent = 0
        for applicant in applicants:
            recipients = [applicant.email]
            if not Email.objects.filter(to=recipients,
                                        template=template).exists():
                mail.send(
                    recipients,
                    sender=email_from,
                    template=template_name,
                    # If emails rendered on delivery, they will store
                    # value of the template id. It makes `exists`
                    # method above works correctly.
                    render_on_delivery=True,
                    backend='ses',
                )
                sent += 1
        self.stdout.write(f"Emails generated {sent}.")
