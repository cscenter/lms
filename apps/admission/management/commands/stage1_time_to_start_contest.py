from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.models import Test
from admission.services import get_email_from

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """
    Send notification to those who applied but haven't yet started the contest.
    """

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-testing-reminder"

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options['template_pattern']
        self.validate_templates(campaigns, [template_name_pattern])

        generated = 0
        for campaign in campaigns:
            email_from = get_email_from(campaign)
            template_name = self.get_template_name(campaign, template_name_pattern)
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
