# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from ._utils import CurrentCampaignMixin, EmailTemplateMixin, validate_templates
from admission.services import get_email_from


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """
    Updates applicant status to PERMIT_TO_EXAM if they passed testing
    (score >= passing_score) and sends email to applicant about this event.

    Note:
        Generate exam records with preserved contest id first if email
        includes link to the exam contest or use --skip-exam-invitation
    """

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-testing-success"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--skip-exam-invitation', action="store_true",
            help='Omits exam record validation')

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        template_name_pattern = options['template_pattern']
        self.validate_templates(campaigns, template_name_pattern)

        skip_exam_invitation = options['skip_exam_invitation']

        for campaign in campaigns:
            self.stdout.write(str(campaign))
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write(f"Passing score for campaign '{campaign}' must be non zero. Skip")
                continue

            template_name = self.get_template_name(campaign, template_name_pattern)
            template = get_email_template(template_name)

            email_from = get_email_from(campaign)

            applicants = (Applicant.objects
                          .filter(campaign=campaign,
                                  online_test__score__gte=testing_passing_score)
                          .values("pk",
                                  "online_test__score",
                                  "online_test__yandex_contest_id",
                                  "exam__yandex_contest_id",
                                  "yandex_login",
                                  "email",
                                  "status"))
            total = 0
            generated = 0
            for a in applicants:
                total += 1
                if a["status"] is not None:
                    msg = f"\tApplicant {a['pk']} already has status {a['status']}. Skip"
                    self.stdout.write(msg)
                    continue
                recipients = [a["email"]]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    context = {
                        'LOGIN': a["yandex_login"],
                        'TEST_SCORE': int(a["online_test__score"]),
                        'TEST_CONTEST_ID': a["online_test__yandex_contest_id"],
                        'EXAM_CONTEST_ID': a["exam__yandex_contest_id"],
                    }
                    if not skip_exam_invitation and context['EXAM_CONTEST_ID'] is None:
                        self.stdout.write(f"No exam contest id were provided for applicant {a['pk']}. Skip")
                        continue
                    # Update status and send email
                    with transaction.atomic():
                        (Applicant.objects
                         .filter(pk=a["pk"])
                         .update(status=Applicant.PERMIT_TO_EXAM))
                        mail.send(
                            recipients,
                            sender=email_from,
                            template=template,
                            context=context,
                            # If emails rendered on delivery, they will store
                            # value of the template id. It makes `exists`
                            # method above works correctly.
                            render_on_delivery=True,
                            backend='ses',
                        )
                        generated += 1
            self.stdout.write(f"    total: {total}")
            self.stdout.write(f"    updated: {generated}")
        self.stdout.write("Done")
