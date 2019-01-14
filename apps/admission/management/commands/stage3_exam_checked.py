# -*- coding: utf-8 -*-
import math
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from ._utils import ValidateTemplatesMixin, CurrentCampaignsMixin
from admission.models import Applicant, Exam


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    TEMPLATE_TYPE = "exam-checked"
    help = 'Generate mails about check completeness'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')

    def handle(self, *args, **options):
        city_code = options["city"] if options["city"] else None
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        self.validate_templates(campaigns, types=[self.TEMPLATE_TYPE])

        generated = 0
        for campaign in campaigns:
            template_name = self.get_template_name(campaign, self.TEMPLATE_TYPE)
            template = get_email_template(template_name)
            results = (
                Exam.objects
                .filter(applicant__campaign=campaign.pk)
                .exclude(applicant__status=Applicant.REJECTED_BY_CHEATING)
                # TODO: restrict selected data
                .select_related("applicant")
            )
            for e in results.iterator():
                applicant = e.applicant
                recipients = [applicant.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    pluralized_scores = []
                    for v in e.details["scores"].values():
                        try:
                            v = int(v)
                            plural_part = self.pluralize(v)
                        except ValueError:
                            plural_part = "а"
                        pluralized_scores.append([v, plural_part])
                    context = {
                        "total": str(e.score),
                        "scores": pluralized_scores
                    }
                    mail.send(
                        recipients,
                        sender='CS центр <info@compscicenter.ru>',
                        template=template,
                        context=context,
                        render_on_delivery=False,
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
