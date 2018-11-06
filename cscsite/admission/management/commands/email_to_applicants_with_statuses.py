from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Queue email for applicants with statuses provided through arguments.

    Example:
        ./manage.py email_to_applicants_with_statuses --city=nsk --statuses=interview_completed,rejected_interview,accept,accept_if,volunteer --template=delay
    """

    def add_arguments(self, parser):
        # TODO: provide `context` field
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')
        parser.add_argument(
            '--template', type=str,
            help='Post office email template type. Template name for each '
                 'campaign is predefined and equal to ' +
                 self.TEMPLATE_REGEXP)
        parser.add_argument(
            '--statuses', type=str,
            help='Comma separated Applicant.STATUS values')
        parser.add_argument(
            '--from', type=str,
            default='CS центр <info@compscicenter.ru>',
            help='Override default `From` header')

    def get_template_name(self, campaign, type):
        return self.TEMPLATE_REGEXP.format(year=campaign.year,
                                           city_code=campaign.city.code,
                                           type=type)

    def handle(self, *args, **options):
        city_code = options["city"]
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        statuses = options['statuses']
        if not statuses:
            raise CommandError("Provide `--statuses` from Applicant.STATUS")
        all_statuses = {code for code, _ in Applicant.STATUS}
        statuses = [s.strip() for s in statuses.split(",")]
        for s in statuses:
            if s not in all_statuses:
                raise CommandError(f"Unknown status `{s}`")

        header_from = options["from"]
        template_type = options['template']
        if not template_type:
            raise CommandError(f"Provide template type")
        self.validate_templates(campaigns, types=[template_type])

        for campaign in campaigns:
            self.stdout.write(f"{campaign}:")
            template_name = self.get_template_name(campaign, template_type)
            template = get_email_template(template_name)
            generated = 0
            applicants = (Applicant.objects
                          .filter(campaign=campaign, status__in=statuses)
                          .only("pk", "email"))
            for a in applicants:
                recipient = a.email
                if not Email.objects.filter(to=recipient,
                                            template=template).exists():
                    mail.send(
                        recipient,
                        sender=header_from,
                        template=template,
                        # Render on delivery, we have no really big amount of
                        # emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
            self.stdout.write("  Generated emails: {}".format(generated))
            self.stdout.write("  Done")
