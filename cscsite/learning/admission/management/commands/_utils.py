# -*- coding: utf-8 -*-
from learning.admission.models import Campaign


class CurrentCampaignsMixin(object):
    CURRENT_CAMPAIGNS_AGREE = "Check current campaigns. Continue? (y/n): "

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
            self.stdout.write(str(campaign))
        self.stdout.write("")
        return campaigns

    def get_current_campaign_ids(self):
        return [c.pk for c in self.get_current_campaigns()]


class HandleErrorsMixin(object):
    @staticmethod
    def handle_errors(result):
        if result.has_errors():
            for error in result.base_errors:
                print(error)
            for line, errors in result.row_errors():
                for error in errors:
                    print("line {} - {}".format(line + 1, error.error))
