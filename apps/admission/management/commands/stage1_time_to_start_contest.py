from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.constants import ChallengeStatuses
from admission.models import Test
from admission.services import EmailQueueService

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

        for campaign in campaigns:
            self.stdout.write(str(campaign))
            template_name = self.get_template_name(campaign, template_name_pattern)
            template = get_email_template(template_name)
            queryset = (Test.objects
                        .filter(applicant__campaign_id=campaign.pk,
                                applicant__is_unsubscribed=False,
                                score__isnull=True,
                                status=ChallengeStatuses.REGISTERED)
                        .values("applicant__email",
                                "applicant__yandex_login",
                                "yandex_contest_id"))

            generated = EmailQueueService.time_to_start_yandex_contest(
                campaign=campaign,
                template=template,
                participants=queryset.iterator()
            )
            self.stdout.write("total: {}".format(queryset.count()))
            self.stdout.write("new: {}".format(generated))
        self.stdout.write("Done")
