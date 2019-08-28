# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin
from admission.models import Test, Applicant


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Updates applicant status to REJECTED_BY_TEST if they failed testing, then
    send notification to them.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--skip-context', action='store_true',
            dest='skip_context',
            help='Skip email context')

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        template_type = "testing-fail"
        self.validate_templates(campaigns, types=[template_type])

        for campaign in campaigns:
            self.stdout.write(str(campaign))
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write("Zero testing passing score "
                                  "for {}. Skip".format(campaign))
                continue

            template_name = self.get_template_name(campaign, template_type)
            template = get_email_template(template_name)

            applicants = (Applicant.objects
                          .filter(campaign_id=campaign.pk)
                          .filter(Q(online_test__score__lt=testing_passing_score) |
                                  Q(online_test__score__isnull=True))
                          .values("pk",
                                  "online_test__score",
                                  "yandex_login",
                                  "email"))
            total = 0
            generated = 0
            for a in applicants:
                total += 1
                context = {}
                if not options['skip_context']:
                    if a["online_test__score"] is None:
                        score = 0
                    else:
                        score = int(a["online_test__score"])
                    assert score < testing_passing_score
                    context = {
                        'LOGIN': a["yandex_login"],
                        'SCORE': score,
                    }
                recipients = [a["email"]]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    with transaction.atomic():
                        (Applicant.objects
                         .filter(pk=a["pk"])
                         .update(status=Applicant.REJECTED_BY_TEST))
                        mail.send(
                            recipients,
                            sender='CS центр <info@compscicenter.ru>',
                            template=template,
                            context=context,
                            # If emails rendered on delivery, they will store
                            # value of the template id. It makes `exists`
                            # method above works correctly.
                            render_on_delivery=True,
                            backend='ses',
                        )
                        generated += 1
            self.stdout.write(f"    Processed: {total}")
            self.stdout.write(f"    New emails: {generated}")
        self.stdout.write("Done")
