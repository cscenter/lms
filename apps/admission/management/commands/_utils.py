import ast
from typing import List, Iterable

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.db.models import Q
from post_office.models import EmailTemplate
from post_office.utils import get_email_template

from admission.models import Campaign, Contest

APPROVAL_DIALOG = "There is no undo. Only 'y' will be accepted to confirm.\n\nEnter a value: "


def validate_template(template_name: str):
    """Checks all email template are exists."""
    try:
        get_email_template(template_name)
    except EmailTemplate.DoesNotExist:
        raise ValidationError(f"Email template `{template_name}` not found")


def validate_campaign_passing_score(campaign):
    if not campaign.online_test_passing_score:
        raise ValidationError(f"Passing score for campaign '{campaign}' must be non zero.")


def validate_campaign_contests(campaign, contest_type):
    """Make sure we have exam contests associated with a campaign."""
    if contest_type not in (type_ for (type_, _) in Contest.TYPES):
        raise ValueError(f"Contest type {contest_type} is not supported")
    qs = (Contest.objects
          .filter(type=contest_type, campaign=campaign))
    if not qs.exists():
        raise ValidationError(f"Contests of type {contest_type} not found for campaign {campaign}")


class CurrentCampaignMixin:
    CURRENT_CAMPAIGNS_AGREE = APPROVAL_DIALOG

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--branch', type=str,
            help='Branch code to restrict current campaigns')

    def get_current_campaigns(self, options, confirm=True, branch_is_required=False):
        branch_code = options["branch"]
        if not branch_code and branch_is_required:
            available = (Campaign.objects
                         .filter(current=True,
                                 branch__site_id=settings.SITE_ID)
                         .select_related('branch'))
            campaigns = [c.branch.code for c in available]
            msg = f"Provide the code of the campaign branch. Options: {campaigns}"
            raise CommandError(msg)

        filter_params = [Q(current=True), Q(branch__site_id=settings.SITE_ID)]
        if branch_code:
            filter_params.append(Q(branch__code=branch_code))
        campaigns = list(Campaign.objects
                         .select_related("branch")
                         .filter(*filter_params))
        self.stdout.write(f"Selected campaigns ({len(campaigns)} total):")
        for campaign in campaigns:
            self.stdout.write(f"\t[{campaign.branch.site}] {campaign.branch.name}, {campaign.year}")
        self.stdout.write("")

        if confirm and input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            raise CommandError("Error asking for approval. Canceled")

        return campaigns


class HandleErrorsMixin:
    @staticmethod
    def handle_errors(result):
        if result.has_errors():
            for error in result.base_errors:
                print(error)
            for line, errors in result.row_errors():
                for error in errors:
                    print("line {} - {}".format(line + 1, error.error))


class EmailTemplateMixin:
    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-{suffix}"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--template-pattern', type=str, default=None,
            help='Overrides default template name pattern')

    def validate_templates(self, campaigns, template_name_patterns: Iterable[str], confirm=True):
        """
        For each campaign validates whether template exists.
        If so ask to confirm and continue.
        """
        errors = []
        templates = set()
        for campaign in campaigns:
            for pattern in template_name_patterns:
                template_name = self.get_template_name(campaign, pattern)
                try:
                    validate_template(template_name)
                    templates.add(template_name)
                except ValidationError as e:
                    errors.append(e)
        if errors:
            msg = "\n".join((e.message for e in errors))
            raise CommandError(f"Validation errors\n{msg}")

        self.stdout.write("\nThese templates will be used in command:")
        self.stdout.write("\n".join(f"\t{t}" for t in templates))
        self.stdout.write("")

        if confirm and input(APPROVAL_DIALOG) != "y":
            raise CommandError("Error asking for approval. Canceled")

    def get_template_name(self, campaign, pattern: str = None, **kwargs):
        pattern = pattern or self.TEMPLATE_PATTERN
        return pattern.format(
            year=campaign.year,
            branch_code=campaign.branch.code,
            **kwargs
        )


class CustomizeQueryMixin:
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('-m', dest='custom_manager', type=str,
                            default='objects', action='store',
                            help='Customize model manager name.')
        parser.add_argument('-f', dest='queryset_filters', type=str,
                            action='append',
                            help='Add `.filter()` expression to queryset'
                                 'Usage example:'
                                 ' -f status__in=["rejected_test"] '
                                 ' -f id__in=[86]')

    def get_manager(self, cls, options):
        manager = getattr(cls, options['custom_manager'] or 'objects')
        queryset_filters = options['queryset_filters']
        if queryset_filters:
            queryset_filters = {
                field: ast.literal_eval(value) for f in queryset_filters
                for field, value in [f.split('=')]
            }
            manager = manager.filter(**queryset_filters)
        manager = manager.order_by()
        return manager
