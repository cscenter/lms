from datetime import datetime

import pytz
from django.core.management.base import BaseCommand, CommandError
from django.utils import formats
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from admission.services import get_email_from
from ._utils import CurrentCampaignMixin, EmailTemplateMixin, \
    CustomizeQueryMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin,
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
            help='`From` header')
        parser.add_argument(
            '--scheduled_time', type=str,
            help='Scheduled time in UTC [YYYY-MM-DD HH:MM]')

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

        scheduled_time = options['scheduled_time']
        time_display = 'now'
        if scheduled_time is not None:
            try:
                scheduled_time = datetime.fromisoformat(scheduled_time)
                scheduled_time = pytz.utc.localize(scheduled_time)
                time_display = formats.date_format(scheduled_time,
                                                   'DATETIME_FORMAT')
            except ValueError:
                raise CommandError(f"Wrong scheduled time format")
        self.stdout.write(f"Scheduled Time [UTC]: {time_display}")
        if input("Continue? y/[n]") != "y":
            self.stdout.write("Canceled")
            return

        manager = self.get_manager(Applicant, options)

        default_from = options["from"]

        for campaign in campaigns:
            self.stdout.write(f"{campaign}")
            email_from = get_email_from(campaign, default=default_from)
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
                        sender=email_from,
                        template=template,
                        scheduled_time=scheduled_time,
                        context={},
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
