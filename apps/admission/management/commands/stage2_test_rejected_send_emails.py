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

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options["template_pattern"]
        self.validate_templates(campaigns, [template_name_pattern])

        for campaign in campaigns:
            self.stdout.write(str(campaign))
            testing_passing_score = campaign.online_test_passing_score
            if not testing_passing_score:
                self.stdout.write(
                    f"Passing score for campaign '{campaign}' must be non zero. Skip"
                )
                continue

            template_name = self.get_template_name(campaign, template_name_pattern)
            template = get_email_template(template_name)

            email_from = get_email_from(campaign)

            applicants = Applicant.objects.filter(
                campaign_id=campaign.pk, status=Applicant.REJECTED_BY_TEST
            ).values(
                "pk",
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
                if score >= testing_passing_score:
                    msg = f"\tWARN Applicant {a['pk']} has passing score >= campaign passing score."
                    self.stdout.write(msg)

                recipients = [a["email"]]
                if not Email.objects.filter(to=recipients, template=template).exists():
                    context = {
                        "YANDEX_LOGIN": a["yandex_login"],
                        "TEST_SCORE": score,
                        "TEST_CONTEST_ID": a["online_test__yandex_contest_id"],
                    }
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
            self.stdout.write(f"    total: {total}")
            self.stdout.write(f"    updated: {generated}")
        self.stdout.write("Done")
