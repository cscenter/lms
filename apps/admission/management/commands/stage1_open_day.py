from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignMixin, EmailTemplateMixin
from admission.services import get_email_from


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-stage1-open-day"
    help = """Generate notification about open day for those who submitted an application form."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--template', type=str,
            help='Post Office template name common for all campaigns')

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        common_template = options['template']
        if common_template:
            try:
                self.check_template_exists(common_template)
            except ValidationError as e:
                raise CommandError(e.message)
        else:
            self.validate_templates_legacy(campaigns, types=['open-day'], validate_campaign_settings=False)

        for campaign in campaigns:
            self.stdout.write(f"Process campaign {campaign}")
            tpl_name = common_template or self.get_template_name(campaign)
            self._generate_notifications(campaign, tpl_name)

    def _generate_notifications(self, campaign, template_name):
        email_from = get_email_from(campaign)
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
                    context={},
                    # If emails rendered on delivery, they will store
                    # value of the template id. It makes `exists`
                    # method above works correctly.
                    render_on_delivery=True,
                    backend='ses',
                )
                sent += 1
        self.stdout.write(f"Emails generated {sent}.")
