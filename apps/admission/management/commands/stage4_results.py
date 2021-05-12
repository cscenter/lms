from collections import Counter

from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.management.commands._utils import (
    CurrentCampaignMixin, CustomizeQueryMixin, EmailTemplateMixin
)
from admission.models import Applicant
from admission.services import get_email_from


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
            self.stdout.write("{}:".format(campaign))
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
                template_name = template_name_patterns[a.status]
                template = get_email_template(template_name)
                recipients = [a.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes
                        # `Email.objects.exists()` work correctly.
                        render_on_delivery=True,
                        context={},
                        backend='ses',
                    )
                    stats[a.status] += 1
            for status, generated in stats.items():
                self.stdout.write(f"Status: {status}. Generated: {generated}")



