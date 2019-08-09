from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin, \
    CustomizeQueryMixin


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin,
              CustomizeQueryMixin, BaseCommand):
    """
    Example:
        Send notification to applicants from Saint-Petersburg who
        passed test with 5 or 6 score

        ./manage.py email_to_applicants --branch=spb --template=admission-2019-try-online -f online_test__score__in=[5,6]
    """
    help = """Send notification to current campaigns applicants"""
    TEMPLATE_REGEXP = "{type}"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        # TODO: provide `context` field
        parser.add_argument(
            '--template', type=str,
            help='Post office email template')
        parser.add_argument(
            '--from', type=str,
            default='CS центр <info@compscicenter.ru>',
            help='Override default `From` header')

    def get_template_name(self, campaign, template):
        return template

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        template_name = options['template']
        if not template_name:
            raise CommandError(f"Provide email template name")
        self.validate_templates(campaigns, types=[template_name])

        manager = self.get_manager(Applicant, options)

        header_from = options["from"]

        for campaign in campaigns:
            self.stdout.write(f"{campaign}")
            template = get_email_template(template_name)
            processed = 0
            new_emails = 0
            applicants = (manager
                          .filter(campaign=campaign)
                          .only("pk", "email"))
            for a in applicants:
                processed += 1
                recipient = a.email
                if not Email.objects.filter(to=recipient,
                                            template=template).exists():
                    mail.send(
                        recipient,
                        sender=header_from,
                        template=template,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes `exists`
                        # method above works correctly.
                        render_on_delivery=True,
                        backend='ses',
                    )
                    new_emails += 1
            self.stdout.write(f"  Processed: {processed}")
            self.stdout.write(f"  New emails: {new_emails}")
        self.stdout.write("Done")
