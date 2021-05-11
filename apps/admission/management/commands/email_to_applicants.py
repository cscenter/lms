from datetime import datetime

import pytz
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand, CommandError
from django.utils import formats

from admission.models import Applicant
from admission.services import get_email_from

from ._utils import (
    CurrentCampaignMixin, CustomizeQueryMixin, EmailTemplateMixin, validate_template
)


class Command(EmailTemplateMixin, CurrentCampaignMixin,
              CustomizeQueryMixin, BaseCommand):
    """
    Example:
        Send notification to applicants from Saint-Petersburg who
        passed test with 5 or 6 score

        ./manage.py email_to_applicants --branch=spb --template=admission-2019-try-online -f online_test__score__in=[5,6]
    """
    help = """Send notification to current campaigns applicants"""
    TEMPLATE_PATTERN = "{type}"

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

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name = options['template_pattern']
        if not template_name:
            raise CommandError("Provide email template name")
        validate_template(template_name)

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

        sender = options["from"]

        for campaign in campaigns:
            self.stdout.write(f"{campaign}")
            email_from = sender or get_email_from(campaign)
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
