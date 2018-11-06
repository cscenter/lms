# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Updates status to PERMIT_TO_EXAM for those who passed testing 
    (score >= passing_score) and adds notification about this event to 
    mailing queue.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--city', type=str,
            help='City code to restrict current campaigns')
        parser.add_argument(
            '--skip-context', action='store_true',
            dest='skip_context',
            help='Skip email context')

    def handle(self, *args, **options):
        city_code = options["city"] if options["city"] else None
        campaigns = self.get_current_campaigns(city_code)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        self.validate_templates(campaigns, types=["testing-success"])

        for campaign in campaigns:
            self.stdout.write(str(campaign))
            total = 0
            generated = 0
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write("Zero testing passing score "
                                  "for {}. Skip".format(campaign))
                continue

            template_type = "testing-success"
            template_name = self.get_template_name(campaign, template_type)
            template = get_email_template(template_name)

            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk,
                                  online_test__score__gte=testing_passing_score)
                          .values("pk",
                                  "online_test__score",
                                  "yandex_id",
                                  "email"))
            for a in applicants:
                total += 1
                # Update status
                (Applicant.objects
                 .filter(pk=a["pk"])
                 .update(status=Applicant.PERMIT_TO_EXAM))
                if options['skip_context']:
                    context = {}
                else:
                    score = int(a["online_test__score"])
                    context = {
                        'SCORE': score,
                        'LOGIN': a["yandex_id"],
                    }
                recipients = [a["email"]]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    mail.send(
                        recipients,
                        sender='CS центр <info@compscicenter.ru>',
                        template=template,
                        context=context,
                        # Render on delivery, we have no really big amount of
                        # emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
            self.stdout.write(f"    Processed: {total}")
            self.stdout.write(f"    Generated emails: {generated}")
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


