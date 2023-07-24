import datetime
from collections import Counter
from typing import Optional
from urllib.parse import urlparse

from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction

from admission.constants import ApplicantStatuses
from admission.management.commands._utils import (
    CurrentCampaignMixin,
    CustomizeQueryMixin,
    EmailTemplateMixin,
)
from admission.models import Acceptance, Applicant
from admission.services import get_email_from
from core.timezone import get_now_utc

INVITE_TO_REGISTRATION = {
    ApplicantStatuses.ACCEPT,
}


class Command(
    EmailTemplateMixin, CustomizeQueryMixin, CurrentCampaignMixin, BaseCommand
):
    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-results-{status}"
    help = """
    Generates emails with final decision based on applicant status.

    Example:
        ./manage.py stage4_results --branch=nsk --template-pattern="csc-admission-{year}-{branch_code}-results-{status}" -f="status__in=['volunteer']"
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--invite",
            dest="invite_to_registration",
            type=str,
            action="store",
            nargs="*",
            metavar="STATUS",
            default=INVITE_TO_REGISTRATION,
            help="Invite participants with statuses to create student profile. "
            "Examples: --invite waiting_for_payment accept. Default: %(default)s)",
            choices=ApplicantStatuses.values.keys(),
        )

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(
            options, confirm=False, branch_is_required=True
        )
        campaign = campaigns[0]
        confirmation_ends_at: Optional[
            datetime.datetime
        ] = campaign.confirmation_ends_at
        if not confirmation_ends_at:
            raise CommandError(
                f"Deadline for confirmation of acceptance for studies is not defined."
            )
        if confirmation_ends_at < get_now_utc():
            raise CommandError(
                f"Deadline for confirmation of acceptance for studies is exceeded."
            )

        invite_to_registration = options["invite_to_registration"]
        self.stdout.write(
            f"Invite to create student profile [statuses]: {' '.join(invite_to_registration)}"
        )

        manager = self.get_manager(Applicant, options)
        applicants = manager.filter(
            campaign_id=campaign.pk
        )
        self.stdout.write(f"Applicants: {len(applicants)}")
        statuses = applicants.values_list("status", flat=True).distinct()
        for applicant in applicants:
            print(applicant.email)
        self.stdout.write(f"Participants with final statuses were found:")
        self.stdout.write("\n".join(statuses))
        template_name_patterns = {}
        for status in statuses:
            pattern = options["template_pattern"] or self.TEMPLATE_PATTERN
            pattern = pattern.replace("{status}", status)
            template_name_patterns[status] = pattern
        self.validate_templates(
            campaigns, template_name_patterns.values(), confirm=False
        )

        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            raise CommandError("Error asking for approval. Canceled")

        email_from = get_email_from(campaign)
        stats = Counter()  # TODO: Why mypy needs type here?
        for applicant in applicants.order_by("status").iterator():
            recipients = [applicant.email]
            template_pattern = template_name_patterns[applicant.status]
            template_name = self.get_template_name(campaign, template_pattern)
            template = get_email_template(template_name)
            is_notified = Email.objects.filter(
                to=recipients, template=template
            ).exists()
            if applicant.status in invite_to_registration:
                is_notified = (
                    is_notified
                    and Acceptance.objects.filter(applicant=applicant).exists()
                )
            if not is_notified:
                with transaction.atomic():
                    if applicant.status in invite_to_registration:
                        acceptance, _ = Acceptance.objects.get_or_create(
                            applicant=applicant
                        )
                        registration_url = urlparse(acceptance.get_absolute_url())
                        context = {
                            "REGISTRATION_RELATIVE_URL": registration_url.path,
                            "AUTH_CODE": acceptance.confirmation_code,
                        }
                    else:
                        context = {}
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes
                        # `Email.objects.exists()` work correctly.
                        render_on_delivery=True,
                        context=context,
                        backend="ses",
                    )
                    stats[applicant.status] += 1
        for status, generated in stats.items():
            self.stdout.write(f"Status: {status}. Generated: {generated}")
