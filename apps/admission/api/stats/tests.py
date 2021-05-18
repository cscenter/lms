import pytest

from django.conf import settings

from admission.tests.factories import CampaignFactory
from core.urls import reverse
from users.tests.factories import CuratorFactory


@pytest.mark.django_db
def test_api_admission_campaign_stages_by_year_smoke(client):
    client.login(CuratorFactory())
    campaign = CampaignFactory()
    url = reverse("stats-api:stats_admission_campaign_stages_by_years", kwargs={
        "branch_id": campaign.branch_id
    }, subdomain=settings.LMS_SUBDOMAIN)
    response = client.get(url)
    assert response.status_code == 200
