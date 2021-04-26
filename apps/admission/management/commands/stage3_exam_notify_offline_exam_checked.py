from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.constants import ChallengeStatuses
from admission.models import Applicant, Exam
from admission.services import get_email_from
from core.jinja2.filters import pluralize

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = 'Generate mails about check completeness'

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-offline-exam-checked"

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options['template_pattern']
        self.validate_templates(campaigns, [template_name_pattern])

        generated = 0
        for campaign in campaigns:
            email_from = get_email_from(campaign)
            template_name = self.get_template_name(campaign, template_name_pattern)
            template = get_email_template(template_name)
            exams = (Exam.objects
                     .filter(applicant__campaign=campaign.pk,
                             applicant__status=Applicant.PERMIT_TO_EXAM,
                             status=ChallengeStatuses.MANUAL)
                     .select_related("applicant"))
            for e in exams.iterator():
                applicant = e.applicant
                recipients = [applicant.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    details = {}
                    for k, value in e.details.items():
                        # Pluralize scores
                        if "Задание" in k:
                            try:
                                value = int(value)
                                plural_part = pluralize(value, "", "a", "ов")
                            except ValueError:
                                plural_part = "а"
                            value = f"{value} балл{plural_part}"
                        details[k] = value
                    context = {
                        "total": str(e.score),
                        "details": details
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
