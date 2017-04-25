# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from post_office import mail
from post_office.models import EmailTemplate, Email
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin
from learning.admission.models import Test, Applicant


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Set status REJECTED_BY_TEST for those who fail testing, also 
    send notification to them.
    """

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

        self.validate_templates(campaigns, types=["testing-fail"])

        total = 0
        generated = 0
        for campaign in campaigns:
            # Get applicants where score is empty or < passing score
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write("Zero testing passing score "
                                  "for {}. Skip".format(campaign))
                continue
            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk)
                          .filter(Q(online_test__score__lt=testing_passing_score) |
                                  Q(online_test__score__isnull=True))
                          .values("pk",
                                  "online_test__score",
                                  "exam__yandex_contest_id",
                                  "yandex_id",
                                  "email")
                          # Weak attempt to process the latest application if
                          # user (with unique email) send more then one.
                          .order_by("-pk"))

            template_type = "testing-fail"
            template_name = self.get_template_name(campaign, template_type)
            template = get_email_template(template_name)

            for a in applicants:
                total += 1
                if a["online_test__score"] is None:
                    score = 0
                else:
                    score = int(a["online_test__score"])
                assert score < testing_passing_score
                # Set status
                (Applicant.objects
                 .filter(pk=a["pk"])
                 .update(status=Applicant.REJECTED_BY_TEST))
                # Add notification to queue
                score_str = str(score) + " балл" + self.pluralize(score)
                context = {
                    'SCORE': score_str,
                    'LOGIN': a["yandex_id"],
                }
                recipients = [a["email"]]
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
                else:
                    self.stdout.write(a["email"])
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


