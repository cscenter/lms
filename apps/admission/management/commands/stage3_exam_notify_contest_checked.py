# -*- coding: utf-8 -*-

from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.constants import ChallengeStatuses
from admission.models import Applicant, Exam
from admission.services import get_email_from

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = 'Generate notifications about contest check completeness'

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-exam-contest-checked"

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options['template_pattern']
        self.validate_templates(campaigns, [template_name_pattern])

        generated = 0
        for campaign in campaigns:
            email_from = get_email_from(campaign)
            template_name = self.get_template_name(campaign, template_name_pattern)
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


