from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.models import Applicant
from admission.services import get_email_from

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """Generate notification about open day for those who submitted an application form."""

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-stage1-open-day"

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options["template_pattern"]
        self.validate_templates(campaigns, [template_name_pattern])

        for campaign in campaigns:
            self.stdout.write(f"Process campaign {campaign}")
            template_name = self.get_template_name(campaign, template_name_pattern)
            self._generate_notifications(campaign, template_name)

    def _generate_notifications(self, campaign, template_name):
        email_from = get_email_from(campaign)
        template = get_email_template(template_name)
        applicants = Applicant.subscribed.filter(campaign_id=campaign.pk)
        sent = 0
        for applicant in applicants:
            recipients = [applicant.email]
            if not Email.objects.filter(to=recipients, template=template).exists():
                mail.send(
                    recipients,
                    sender=email_from,
                    template=template_name,
                    context={},
                    # If emails rendered on delivery, they will store
                    # value of the template id. It makes `exists`
                    # method above works correctly.
                    render_on_delivery=True,
                    backend="ses",
                )
                sent += 1
        self.stdout.write(f"Emails generated {sent}.")
