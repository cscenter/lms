# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.db.models import Q
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin
from admission.models import Test, Applicant


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Updates status to REJECTED_BY_TEST for those who failed testing, then 
    send notification to them.
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

        self.validate_templates(campaigns, types=["testing-fail"])

        for campaign in campaigns:
            self.stdout.write(str(campaign))
            total = 0
            generated = 0
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write("Zero testing passing score "
                                  "for {}. Skip".format(campaign))
                continue

            template_type = "testing-fail"
            template_name = self.get_template_name(campaign, template_type)
            template = get_email_template(template_name)

            # applicants who's score is empty or < passing score
            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk)
                          .filter(Q(online_test__score__lt=testing_passing_score) |
                                  Q(online_test__score__isnull=True))
                          .values("pk",
                                  "online_test__score",
                                  "exam__yandex_contest_id",
                                  "yandex_id",
                                  "email"))
            for a in applicants:
                total += 1
                (Applicant.objects
                 .filter(pk=a["pk"])
                 .update(status=Applicant.REJECTED_BY_TEST))
                # Add notification to queue
                if options['skip_context']:
                    context = {}
                else:
                    if a["online_test__score"] is None:
                        score = 0
                    else:
                        score = int(a["online_test__score"])
                    assert score < testing_passing_score
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
            self.stdout.write(f"    Processed applicants: {total}")
            self.stdout.write(f"    Generated emails: {generated}")
        self.stdout.write("Done")
