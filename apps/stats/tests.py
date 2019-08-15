import json
from datetime import datetime, timedelta

import pytest
import pytz
from django.conf import settings

from admission.tests.factories import ApplicantFactory, CampaignFactory
from core.tests.utils import now_for_branch
from core.timezone import now_local
from core.urls import reverse
from learning.settings import Branches


@pytest.mark.django_db
def test_application_form_stats_empty_results(client, curator):
    start = datetime(year=2018, month=3, day=14, hour=11, tzinfo=pytz.UTC)
    campaign = CampaignFactory(branch__code=Branches.SPB,
                               application_starts_at=start,
                               application_ends_at=start + timedelta(hours=1),
                               year=2018)
    url = reverse("api:stats_admission_application_form_submission",
                  kwargs={"branch_id": campaign.branch.id},
                  subdomain=settings.LMS_SUBDOMAIN)
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert "2018" in data
    assert len(data) == 1
    ApplicantFactory(campaign=campaign, created=start + timedelta(minutes=1))
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data["2018"][0] == 1


@pytest.mark.django_db
def test_application_form_stats(client, curator):
    start = datetime(year=2018, month=3, day=14, hour=11, tzinfo=pytz.UTC)
    campaign = CampaignFactory(branch__code=Branches.SPB,
                               application_starts_at=start,
                               application_ends_at=start + timedelta(days=15),
                               year=2018)
    url = reverse("api:stats_admission_application_form_submission",
                  kwargs={"branch_id": campaign.branch_id},
                  subdomain=settings.LMS_SUBDOMAIN)
    ApplicantFactory(campaign=campaign, created=start - timedelta(hours=1))
    ApplicantFactory.create_batch(3,
                                  campaign=campaign,
                                  created=start + timedelta(hours=1))
    ApplicantFactory(campaign=campaign, created=start + timedelta(days=1))
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert "2018" in data
    assert data["2018"][0] == 3
    assert data["2018"][1] == 4
    # Test partial sums with active campaign
    today = now_for_branch(Branches.SPB)
    start = today - timedelta(days=2)
    current_campaign = CampaignFactory(
        branch__code=Branches.SPB,
        current=True,
        application_starts_at=start,
        application_ends_at=today + timedelta(days=5),
        year=today.year)
    ApplicantFactory(campaign=current_campaign, created=start)
    ApplicantFactory(campaign=current_campaign,
                     created=start + timedelta(days=1))
    ApplicantFactory(campaign=current_campaign,
                     created=today)
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.content)
    today_year = str(today.year)
    assert today_year in data
    stats = data[today_year]
    assert stats[0] == 1
    assert stats[1] == 2
    assert stats[2] == 3
