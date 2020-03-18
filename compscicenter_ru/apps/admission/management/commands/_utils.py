# -*- coding: utf-8 -*-
import ast

from django.core.management import CommandError
from post_office.models import EmailTemplate
from post_office.utils import get_email_template

from admission.models import Campaign


class CurrentCampaignsMixin:
    CURRENT_CAMPAIGNS_AGREE = "The action will affect campaigns above. " \
                              "Continue? (y/n): "

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--branch', type=str,
            help='Branch code to restrict current campaigns')

    def get_current_campaigns(self, options, required=False):
        branch_code = options["branch"]
        if not branch_code and required:
            available = (Campaign.objects.filter(current=True)
                         .select_related('branch'))
            campaigns = [c.branch.code for c in available]
            msg = f"Provide the code of the campaign branch. Options: {campaigns}"
            raise CommandError(msg)

        filter_params = {"current": True}
        if branch_code:
            filter_params["branch__code"] = branch_code
        campaigns = (Campaign.objects
                     .select_related("branch")
                     .filter(**filter_params)
                     .all())
        self.stdout.write("Selected current campaigns ({} total):".format(
            len(campaigns)))
        for campaign in campaigns:
            self.stdout.write(f"  {campaign} [{campaign.branch}]")
        return campaigns

    # FIXME: remove?
    def get_current_campaign_ids(self, options):
        return [c.pk for c in self.get_current_campaigns(options)]


class HandleErrorsMixin:
    @staticmethod
    def handle_errors(result):
        if result.has_errors():
            for error in result.base_errors:
                print(error)
            for line, errors in result.row_errors():
                for error in errors:
                    print("line {} - {}".format(line + 1, error.error))


class ValidateTemplatesMixin:
    TEMPLATE_REGEXP = "admission-{year}-{branch_code}-{type}"

    def validate_templates(self, campaigns, types=None):
        # For each campaign check email template exists and
        # passing score for test results non zero
        check_types = types or ["success", "fail"]
        qs = EmailTemplate.objects.get_queryset()
        errors = []
        for c in campaigns:
            if not c.online_test_passing_score:
                msg = f"Passing score for campaign '{c}' must be non zero"
                errors.append(msg)
            for t in check_types:
                template_name = self.get_template_name(c, t)
                try:
                    # Use post office method for caching purpose
                    get_email_template(template_name)
                except EmailTemplate.DoesNotExist:
                    msg = f"Email template `{template_name}` not found"
                    errors.append(msg)
        if errors:
            raise CommandError("\n".join(errors))

    def get_template_name(self, campaign, suffix):
        return self.TEMPLATE_REGEXP.format(
            year=campaign.year,
            branch_code=campaign.branch.code,
            type=suffix
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
