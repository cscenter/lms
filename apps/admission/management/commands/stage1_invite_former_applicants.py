from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand, CommandError

from admission.models import Applicant, Campaign
from admission.services import get_email_from

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """
    Those who didn't pass admission campaign in the past N years (2 by default)
    and didn't apply for the current, have a chance to submit an application
    form until deadline.
    """

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-invite-former-applicants"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--years",
            type=int,
            default=2,
            help="How many years before the current campaign should be taken into account.",
        )

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options)

        template_name_pattern = options["template_pattern"]
        self.validate_templates(campaigns, [template_name_pattern])

        number_of_years = options["years"]
        if number_of_years < 1:
            raise CommandError(f"Number of years must be >= 1")

        for campaign in campaigns:
            self.stdout.write(f"Process campaign {campaign}")
            in_range = [campaign.year - number_of_years, campaign.year - 1]
            template_name = self.get_template_name(campaign, template_name_pattern)
            self._generate_notifications(campaign, in_range, template_name)

    def _generate_notifications(self, current_campaign, in_range, template_name):
        email_from = get_email_from(current_campaign)
        prev_campaigns = list(
            Campaign.objects.filter(
                branch=current_campaign.branch, year__range=in_range
            ).order_by("-year")
        )
        if not prev_campaigns:
            self.stdout.write(f"No previous campaigns for {current_campaign}")
            return
        else:
            for c in prev_campaigns:
                self.stdout.write(f"{c}")
            if input("Continue? [y/n] ") != "y":
                return

        exclude_statuses = [
            Applicant.ACCEPT,
            Applicant.ACCEPT_IF,
            Applicant.VOLUNTEER,
            Applicant.THEY_REFUSED,
            Applicant.WAITING_FOR_PAYMENT,
            Applicant.ACCEPT_PAID,
            Applicant.REJECTED_BY_CHEATING,
        ]
        failed_in_prev_campaigns = (
            Applicant.subscribed.filter(campaign__in=prev_campaigns)
            .exclude(status__in=exclude_statuses, user__isnull=False)
            .distinct()
            .values_list("email", flat=True)
        )
        total = 0
        generated = 0
        template = get_email_template(template_name)
        for email in failed_in_prev_campaigns:
            total += 1
            is_already_applied = Applicant.objects.filter(
                campaign_id=current_campaign.pk, email=email
            ).exists()
            if not is_already_applied:
                recipients = [email]
                if not Email.objects.filter(to=recipients, template=template).exists():
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template_name,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes `exists`
                        # method above works correctly.
                        render_on_delivery=True,
                        context={},
                        backend="ses",
                    )
                    generated += 1
        self.stdout.write(
            f"Total: {total}\nGenerated {generated}\nAlready applied: {total - generated}"
        )
