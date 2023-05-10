from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from admission.models import Applicant
from admission.services import get_email_from

from ._utils import (
    CurrentCampaignMixin,
    EmailTemplateMixin,
    validate_campaign_passing_score,
)


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """
    Sends email to applicants about passing the test.

    Generate exam records with preserved contest id first if email
    includes link to the exam contest or use --skip-exam-invitation
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--skip-exam-invitation",
            action="store_true",
            default=True,
            help="Omits exam record validation",
        )
        parser.add_argument(
            "--send_emails",
            action="store_true",
            default=False,
            dest="send_emails",
            help="Run email sending."
        )
        parser.add_argument(
            "--new_track",
            action="store_true",
            default=False,
            dest="new_track",
            help="Update statuses for 'new track' applicants."
        )
        parser.add_argument(
            "--applicant_id",
            dest="applicant_id",
            help="Send email only for applicant.id == applicant_id"
        )

    def handle(self, *args, **options):
        new_track = options.get('new_track')
        send_emails = options.get('send_emails')
        applicant_id = options.get('applicant_id')
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options["template_pattern"]
        year = campaigns[0].year
        if not template_name_pattern:
            if new_track:
                template_name_pattern = f"shad-admission-{year}-alt-testing-success"
            else:
                template_name_pattern = f"shad-admission-{year}-testing-success"
        self.validate_templates(campaigns, [template_name_pattern])

        skip_exam_invitation = options["skip_exam_invitation"]

        for campaign in campaigns:
            self.stdout.write(str(campaign))

            template_name = self.get_template_name(campaign, template_name_pattern)
            template = get_email_template(template_name)

            email_from = get_email_from(campaign)

            filters = {
                "campaign": campaign,
                "status": Applicant.PERMIT_TO_EXAM,
                "data__new_track": new_track,
            }
            if applicant_id:
                filters["id"] = applicant_id
            applicants = Applicant.objects.filter(
                **filters
            ).values(
                "pk",
                "first_name",
                "online_test__score",
                "online_test__yandex_contest_id",
                "exam__yandex_contest_id",
                "yandex_login",
                "email",
                "status",
            )
            total = 0
            generated = 0
            for a in applicants:
                total += 1
                if not skip_exam_invitation and a["exam__yandex_contest_id"] is None:
                    self.stdout.write(
                        f"No exam contest id were provided for applicant {a['pk']}. Skip"
                    )
                    continue
                recipients = [a["email"]]
                if not Email.objects.filter(to=recipients, template=template).exists():
                    context = {
                        "FIRST_NAME": a["first_name"],
                        "YANDEX_LOGIN": a["yandex_login"],
                        "TEST_SCORE": int(a["online_test__score"]),
                        "TEST_CONTEST_ID": a["online_test__yandex_contest_id"],
                        "EXAM_CONTEST_ID": a["exam__yandex_contest_id"],
                    }
                    if send_emails:
                        mail.send(
                            recipients,
                            sender=email_from,
                            template=template,
                            context=context,
                            # If emails rendered on delivery, they will store
                            # value of the template id. It makes `exists`
                            # method above works correctly.
                            render_on_delivery=True,
                            backend="ses",
                        )
                        generated += 1
                    else:
                        print(recipients[0], template)
            self.stdout.write(f"    total: {total}")
            self.stdout.write(f"    updated: {generated}")
            self.stdout.write(f"    is sent: {send_emails}")
        self.stdout.write("Done")
