# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.constants import ChallengeStatuses
from admission.models import Applicant, Exam
from ._utils import EmailTemplateMixin, CurrentCampaignMixin
from admission.services import get_email_from


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    TEMPLATE_TYPE = "exam-contest-checked"
    help = 'Generate notifications about contest check completeness'

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        self.validate_templates(campaigns, types=[self.TEMPLATE_TYPE])

        generated = 0
        for campaign in campaigns:
            email_from = get_email_from(campaign)
            template_name = self.get_template_name(campaign, self.TEMPLATE_TYPE)
            template = get_email_template(template_name)
            exam_results = (
                Exam.objects
                .filter(applicant__campaign=campaign.pk,
                        applicant__status=Applicant.PERMIT_TO_EXAM,
                        applicant__is_unsubscribed=False,
                        status__in=[ChallengeStatuses.NEW,
                                    ChallengeStatuses.REGISTERED])
                .select_related("applicant")
            )

            for e in exam_results:
                if e.status == ChallengeStatuses.NEW:
                    self.stdout.write(f"{e} wasn't registered in the contest!")
                    continue
                applicant = e.applicant
                recipients = [applicant.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    context = {
                        'SCORE': str(e.score if e.score is not None else 0),
                        'CONTEST_ID': e.yandex_contest_id,
                    }
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template,
                        context=context,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes
                        # `Email.objects.exists()` work correctly.
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
        self.stdout.write("Generated emails: {}".format(generated))
        self.stdout.write("Done")


