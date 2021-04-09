# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from ._utils import CurrentCampaignMixin, EmailTemplateMixin
from admission.models import Applicant, Test
from admission.services import get_email_from


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    TEMPLATE_TYPE = "testing-reminder"
    help = """
    Send notification to those who applied but haven't yet started the contest.
    """

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
            self.validate_templates(campaigns, types=[self.TEMPLATE_TYPE],
                                    validate_campaign_settings=False)

        generated = 0
        for campaign in campaigns:
            email_from = get_email_from(campaign)
            template_name = common_template or self.get_template_name(campaign, type=self.TEMPLATE_TYPE)
            template = get_email_template(template_name)
            tests = (Test.objects
                     .filter(applicant__campaign_id=campaign.pk,
                             applicant__is_unsubscribed=False,
                             score__isnull=True,
                             status=Test.REGISTERED)
                     .values("applicant__email",
                             "yandex_contest_id"))

            for t in tests.iterator():
                recipients = [t["applicant__email"]]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template,
                        context={
                          "CONTEST_ID": t["yandex_contest_id"]
                        },
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
        self.stdout.write("Generated emails: {}".format(generated))
        self.stdout.write("Done")
