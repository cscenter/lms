# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now
from post_office import mail
from post_office.models import EmailTemplate, Email
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin
from learning.admission.models import Test, Applicant


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    # TODO: scheduled time support?
    # TODO: priority level support?
    TEMPLATE_REGEXP = "admission-{year}-{city_code}-test-{type}"
    help = """
    Generate mailing list with online test results based on passing score.

    Template string for email templates:
        {}
        type: [success|fail]
    """.format(TEMPLATE_REGEXP)

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

        self.validate_templates(campaigns)

        total = 0
        generated = 0
        for campaign in campaigns:
            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk)
                          .values("online_test__score",
                                  "exam__yandex_contest_id",
                                  "yandex_id",
                                  "email"))

            for a in applicants:
                total += 1
                if a["online_test__score"] is None:
                    score = 0
                else:
                    score = int(a["online_test__score"])
                score_str = str(score) + " балл" + self.pluralize(score)
                context = {
                    'SCORE': score_str,
                    'LOGIN': a["yandex_id"],
                }
                if score < campaign.online_test_passing_score:
                    template_type = "fail"
                else:
                    template_type = "success"
                    assert a["exam__yandex_contest_id"] is not None
                    context['LINK'] = "https://contest.yandex.ru/contest/{}/".format(a["exam__yandex_contest_id"])
                recipients = [a["email"]]
                template_name = self.get_template_name(campaign, template_type)
                template = get_email_template(template_name)
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender='info@compscicenter.ru',
                        template=template,
                        context=context,
                        # Render on delivery, we have no really big amount of
                        # emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
        self.stdout.write("Processed applicants: {}".format(total))
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


