# TODO: Нельзя сохранить и university и university_other (приоритет у university_other)
# TODO: where_did_you_learn , если есть с суффиксом _other, то убедиться, что в where_did_you_learn другое? выставить самим
# FIXME: тест на создание нового универа, т.к. уже было падение по этой причине
from datetime import timedelta

import pytest

from admission.tests.factories import CampaignFactory, ApplicantFactory
from admission.views import SESSION_LOGIN_KEY
from core.factories import UniversityFactory
from core.timezone import now_local
from core.urls import reverse
from learning.settings import Branches
from learning.tests.factories import BranchFactory


@pytest.mark.django_db
def test_application_form_inactive_or_past_campaign(client):
    url = reverse("api:applicant_create")
    today = now_local(Branches.SPB)
    campaign = CampaignFactory(current=True, city_id=Branches.SPB,
                               application_starts_at=today - timedelta(days=2),
                               application_ends_at=today + timedelta(days=2))
    form_data = {
        "campaign": campaign.id
    }
    response = client.post(url, form_data)
    assert response.status_code == 400
    assert "campaign" not in response.data
    campaign.application_ends_at = today - timedelta(days=1)
    campaign.save()
    response = client.post(url, form_data)
    assert response.status_code == 400
    assert "campaign" in response.data


@pytest.mark.django_db
def test_application_form_preferred_study_programs(client):
    """`preferred_study_programs` is mandatory for on-campus branches"""
    url = reverse("api:applicant_create")
    today = now_local(Branches.SPB)
    campaign = CampaignFactory(current=True, city_id=Branches.SPB,
                               application_starts_at=today - timedelta(days=2),
                               application_ends_at=today + timedelta(days=2))
    university = UniversityFactory()
    form_data = ApplicantFactory.build_application_form(
        campaign=campaign,
        university=university)
    if "preferred_study_programs" in form_data:
        del form_data["preferred_study_programs"]
    assert not campaign.city.is_online_branch, "preferred_study_programs has no sense for distance branch"
    # Yandex.Login stored in client session and will override form value
    # in any case
    session = client.session
    session[SESSION_LOGIN_KEY] = 'yandex_login'
    session.save()
    response = client.post(url, form_data)
    assert response.status_code == 400
    assert "preferred_study_programs" in response.data


@pytest.mark.django_db
def test_application_form_living_place(client):
    """`living_place` is mandatory for distance branch"""
    url = reverse("api:applicant_create")
    today = now_local(Branches.SPB)
    branch = BranchFactory(code=Branches.DISTANCE, is_remote=True)
    campaign = CampaignFactory(current=True,
                               city_id=Branches.SPB,
                               branch=branch,
                               application_starts_at=today - timedelta(days=2),
                               application_ends_at=today + timedelta(days=2))
    assert campaign.branch.is_remote
    university = UniversityFactory()
    form_data = ApplicantFactory.build_application_form(
        campaign=campaign,
        university=university)
    if "living_place" in form_data:
        del form_data["living_place"]
    # Yandex.Login stored in client session and will override form value
    # in any case
    session = client.session
    session[SESSION_LOGIN_KEY] = 'yandex_login'
    session.save()
    response = client.post(url, form_data)
    assert response.status_code == 400
    assert "living_place" in response.data
    assert "preferred_study_programs" not in response.data
