# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.db import transaction
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignsMixin, ValidateTemplatesMixin


class Command(ValidateTemplatesMixin, CurrentCampaignsMixin, BaseCommand):
    help = """
    Updates applicant status to PERMIT_TO_EXAM if they passed testing
    (score >= passing_score) and adds notification about this event to 
    mailing queue.

    Note:
        Generate exam records with preserved contest id first if notification
        includes link to the contest.
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

        template_type = "testing-success"
        self.validate_templates(campaigns, types=[template_type])

        for c in campaigns:
            self.stdout.write(str(c))
            testing_passing_score = c.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write(f"Zero testing passing score for {c}. Skip")
                continue

            template_name = self.get_template_name(c, template_type)
            template = get_email_template(template_name)

            applicants = (Applicant.objects
                          .filter(campaign_id=c.pk,
                                  online_test__score__gte=testing_passing_score)
                          .values("pk",
                                  "online_test__score",
                                  "exam__yandex_contest_id",
                                  "yandex_login",
                                  "email",
                                  "status"))
            total = 0
            generated = 0
            for a in applicants:
                total += 1
                context = {}
                if not options['skip_context']:
                    score = int(a["online_test__score"])
                    context = {
                        'LOGIN': a["yandex_login"],
                        'SCORE': score,
                        'CONTEST_ID': a["exam__yandex_contest_id"],
                    }
                recipients = [a["email"]]
                if a["status"] is not None:
                    msg = f"Applicant {a['pk']} has status {a['status']}. Skip"
                    self.stdout.write(msg)
                    continue
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    with transaction.atomic():
                        # Update status
                        (Applicant.objects
                         .filter(pk=a["pk"])
                         .update(status=Applicant.PERMIT_TO_EXAM))
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
