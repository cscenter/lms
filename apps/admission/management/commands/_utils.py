# -*- coding: utf-8 -*-
import ast
from typing import List

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.db.models import Q
from post_office.models import EmailTemplate
from post_office.utils import get_email_template

from admission.models import Campaign


def validate_templates(template_names: List[str]):
    """Checks all email template are exists."""
    errors = []
    for template_name in template_names:
        try:
            get_email_template(template_name)
        except EmailTemplate.DoesNotExist:
            error = ValidationError(f"Email template `{template_name}` not found")
            errors.append(error)
    return errors


class CurrentCampaignMixin:
    CURRENT_CAMPAIGNS_AGREE = "There is no undo. Only 'y' will be accepted to confirm.\n\nEnter a value: "

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--branch', type=str,
            help='Branch code to restrict current campaigns')

    def get_current_campaigns(self, options, required=False):
        branch_code = options["branch"]
        if not branch_code and required:
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
        campaigns = (Campaign.objects
                     .select_related("branch")
                     .filter(*filter_params)
                     .all())
        self.stdout.write("Selected campaigns ({} total):".format(
            len(campaigns)))
        for campaign in campaigns:
            self.stdout.write(f"[{campaign.branch.site}] {campaign.branch.name}, {campaign.year}")
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
    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-{type}"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--template-pattern', type=str, default=None,
            help='Overrides default template name pattern')

    def validate_templates_legacy(self, campaigns, types=None,
                                  validate_campaign_settings=True):
        # For each campaign check email template exists and
        # passing score for test results non zero
        check_types = types or ["success", "fail"]
        errors = []
        for campaign in campaigns:
            if validate_campaign_settings:
                self._validate_campaign_settings(campaign, errors)
            for t in check_types:
                template_name = self.get_template_name(campaign, type=t)
                try:
                    self.check_template_exists(template_name)
                except ValidationError as e:
                    errors.append(e.message)
        if errors:
            raise CommandError("\n".join(errors))

    def validate_templates(self, campaigns, template_name_pattern):
        errors = []
        for campaign in campaigns:
            template_name = self.get_template_name(campaign, template_name_pattern)
            errors.extend(validate_templates([template_name]))
        if errors:
            raise CommandError("\n".join((e.message for e in errors)))

    def check_template_exists(self, template_name):
        try:
            # Use post office method for caching purpose
            get_email_template(template_name)
        except EmailTemplate.DoesNotExist:
            raise ValidationError(f"Email template `{template_name}` not found")

    # FIXME: Not sure why this validation is in templates
    def _validate_campaign_settings(self, campaign, errors):
        if not campaign.online_test_passing_score:
            msg = f"Passing score for campaign '{campaign}' must be non zero"
            errors.append(msg)

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
