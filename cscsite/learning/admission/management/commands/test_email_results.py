# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now
from post_office import mail
from post_office.models import EmailTemplate
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin
from learning.admission.models import Test, Applicant


class Command(CurrentCampaignsMixin, BaseCommand):
    # TODO: scheduled time support?
    # TODO: priority level support?
    TEMPLATE_REGEXP = "admission-{year}-{city_code}-test-{type}"
    help = """
    Generate mailing list with online test results based on passing score
    
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

        for campaign in campaigns:
            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk)
                          .values("online_test__score",
                                  "exam__yandex_contest_id",
                                  "yandex_id",
                                  "email"))

            for a in applicants:
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
                    context['LINK'] = "https://contest.yandex.ru/contest/{}/".format(a["exam__yandex_contest_id"])
                mail.send(
                    [a["email"]],
                    sender='info@compscicenter.ru',
                    template=self.get_template_name(campaign, template_type),
                    context=context,
                    # Render on delivery, we have no really big amount of
                    # emails to save CPU time
                    render_on_delivery=True,
                    backend='ses',
                )
        self.stdout.write("Done")

    def get_template_name(self, campaign, type):
        today = now()
        year = today.year
        return self.TEMPLATE_REGEXP.format(
            year=year,
            city_code=campaign.city_id,
            type=type
        )

    def validate_templates(self, campaigns):
        # For each campaign check email template exists and
        # passing score for test results non zero
        qs = EmailTemplate.objects.get_queryset()
        for campaign in campaigns:
            if not campaign.online_test_passing_score:
                raise CommandError("Passing score for campaign '{}'"
                                   " must be non zero".format(campaign))
            try:
                template_name = self.get_template_name(campaign, "success")
                # Use post office method for caching purpose
                get_email_template(template_name)
            except EmailTemplate.DoesNotExist:
                raise CommandError("Email template {} "
                                   "not found".format(template_name))
            try:
                template_name = self.get_template_name(campaign, "fail")
                get_email_template(template_name)
            except EmailTemplate.DoesNotExist:
                raise CommandError("Email template {} "
                                   "not found".format(template_name))

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


