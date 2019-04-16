# -*- coding: utf-8 -*-
from django.core.management import CommandError
from post_office.models import EmailTemplate
from post_office.utils import get_email_template

from admission.models import Campaign


class CurrentCampaignsMixin:
    CURRENT_CAMPAIGNS_AGREE = "The action will affect campaigns above. " \
                              "Continue? (y/n): "

    def get_current_campaigns(self, city_code=None):
        filter_params = {"current": True}
        if city_code:
            filter_params["city_id"] = city_code
        campaigns = (Campaign.objects
                     .select_related("city")
                     .filter(**filter_params)
                     .all())
        self.stdout.write("Selected current campaigns ({} total):".format(
            len(campaigns)))
        for campaign in campaigns:
            self.stdout.write(f"  {campaign} [{campaign.city_id}]")
        return campaigns

    def get_current_campaign_ids(self, city_code=None):
        return [c.pk for c in self.get_current_campaigns(city_code)]


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
    TEMPLATE_REGEXP = "admission-{year}-{city_code}-{type}"

    def validate_templates(self, campaigns, types=None):
        # For each campaign check email template exists and
        # passing score for test results non zero
        check_types = types or ["success", "fail"]
        qs = EmailTemplate.objects.get_queryset()
        for campaign in campaigns:
            if not campaign.online_test_passing_score:
                raise CommandError("Passing score for campaign '{}'"
                                   " must be non zero".format(campaign))
            for t in check_types:
                template_name = self.get_template_name(campaign, t)
                try:
                    # Use post office method for caching purpose
                    get_email_template(template_name)
                except EmailTemplate.DoesNotExist:
                    raise CommandError("Email template {} "
                                       "not found".format(template_name))

    def get_template_name(self, campaign, type):
        return self.TEMPLATE_REGEXP.format(
            year=campaign.year,
            city_code=campaign.city_id,
            type=type
        )
