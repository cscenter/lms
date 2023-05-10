from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.models import Applicant
from admission.services import get_email_from

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """Sends email to applicants about failing the test."""

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-testing-fail"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--send_emails",
            action="store_true",
            default=False,
            dest="send_emails",
            help="Run email sending."
        )
        parser.add_argument(
            "--applicant_id",
            dest="applicant_id",
            help="Send email only for applicant.id == applicant_id"
        )

    def handle(self, *args, **options):
        send_emails = options.get('send_emails')
        applicant_id = options.get('applicant_id')
        campaigns = self.get_current_campaigns(options)

        for campaign in campaigns:
            self.stdout.write(str(campaign))

            email_from = get_email_from(campaign)

            filters = {
                "campaign": campaign,
                "status__in": [Applicant.REJECTED_BY_TEST, Applicant.REJECTED_BY_CHEATING],
            }
            if applicant_id:
                filters["id"] = applicant_id
            applicants = Applicant.objects.filter(
                **filters
            ).values(
                "pk",
                "first_name",
                "status",
                "online_test__score",
                "online_test__yandex_contest_id",
                "yandex_login",
                "email",
            )
            total = 0
            generated = 0
            for a in applicants:
                total += 1
                score = (
                    0
                    if a["online_test__score"] is None
                    else int(a["online_test__score"])
                )

                recipients = [a["email"]]

                year = campaigns[0].year
                if a['status'] == Applicant.REJECTED_BY_TEST:
                    template_name = f"shad-admission-{year}-testing-failed"
                elif a['status'] == Applicant.REJECTED_BY_CHEATING:
                    template_name = f"shad-admission-{year}-cheater-testing-failed"
                else:
                    raise NotImplementedError(f"Unexpected applicant status: {a.status}")
                template = get_email_template(template_name)

                if not Email.objects.filter(to=recipients, template=template).exists():
                    context = {
                        "FIRST_NAME": a["first_name"],
                        "YANDEX_LOGIN": a["yandex_login"],
                        "TEST_SCORE": score,
                        "TEST_CONTEST_ID": a["online_test__yandex_contest_id"],
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
