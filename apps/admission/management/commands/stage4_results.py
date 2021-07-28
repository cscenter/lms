from collections import Counter
from urllib.parse import urlparse

from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand
from django.db import transaction

from admission.management.commands._utils import (
    CurrentCampaignMixin, CustomizeQueryMixin, EmailTemplateMixin
)
from admission.models import Acceptance, Applicant
from admission.services import get_email_from
from core.timezone import get_now_utc


class Command(EmailTemplateMixin, CustomizeQueryMixin,
              CurrentCampaignMixin, BaseCommand):
    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-results-{status}"
    help = """
    Generates emails with final decision based on applicant status.

    Example:
        ./manage.py stage4_results --branch=nsk -f="status__in=['volunteer']"
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--from', type=str,
            help='Overrides default `From` header')

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, branch_is_required=True)

        sender = options["from"]

        manager = self.get_manager(Applicant, options)

        for campaign in campaigns:
            self.stdout.write(f"{campaign}:")
            if not campaign.confirmation_ends_at:
                self.stdout.write(f"Deadline for confirmation of acceptance for studies is not defined. Skip")
                continue
            if campaign.confirmation_ends_at < get_now_utc():
                self.stdout.write(f"Deadline for confirmation of acceptance for studies is exceeded. Skip")
                continue
            applicants = manager.filter(campaign_id=campaign.pk)

            template_name_patterns = {}
            statuses = applicants.values_list('status', flat=True).distinct()
            for status in statuses:
                pattern = options['template_pattern'] or self.TEMPLATE_PATTERN
                pattern = pattern.replace("{status}", status)
                template_name_patterns[status] = pattern
            self.validate_templates(campaigns, template_name_patterns.values())

            email_from = sender or get_email_from(campaign)
            stats = Counter()
            for a in applicants.order_by('status').iterator():
                if not Acceptance.objects.filter(applicant=a).exists():
                    template_name = template_name_patterns[a.status]
                    template = get_email_template(template_name)
                    recipients = [a.email]
                    acceptance = Acceptance(applicant=a)
                    registration_url = urlparse(acceptance.get_absolute_url())
                    with transaction.atomic():
                        # FIXME: move to service if it needs to validate email
                        # FIXME: what status is valid for creating acceptance record?
                        acceptance.save()
                        mail.send(
                            recipients,
                            sender=email_from,
                            template=template,
                            # If emails rendered on delivery, they will store
                            # value of the template id. It makes
                            # `Email.objects.exists()` work correctly.
                            render_on_delivery=True,
                            context={
                                "REGISTRATION_RELATIVE_URL": registration_url.path,
                                "CONFIRMATION_CODE": acceptance.confirmation_code
                            },
                            backend='ses',
                        )
                        stats[a.status] += 1
            for status, generated in stats.items():
                self.stdout.write(f"Status: {status}. Generated: {generated}")



