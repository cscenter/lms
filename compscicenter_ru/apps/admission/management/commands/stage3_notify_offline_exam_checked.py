# -*- coding: utf-8 -*-
import math
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.constants import ChallengeStatuses
from ._utils import EmailTemplateMixin, CurrentCampaignMixin
from admission.models import Applicant, Exam
from admission.services import get_email_from


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    TEMPLATE_TYPE = "offline-exam-checked"
    help = 'Generate mails about check completeness'

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
                    for k, v in e.details.items():
                        # Pluralize scores
                        if "Задание" in k:
                            try:
                                v = int(v)
                                plural_part = self.pluralize(v)
                            except ValueError:
                                plural_part = "а"
                            v = f"{v} балл{plural_part}"
                        details[k] = v
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

    # shitty code
    @staticmethod
    def pluralize(value):
        endings = ["", "a", "ов"]
        if value % 100 in (11, 12, 13, 14):
            return endings[2]
        if value % 10 == 1:
            return endings[0]
        if value % 10 in (2, 3, 4):
            return endings[1]
        else:
            return endings[2]
