# TODO: Нельзя сохранить и university и university_other (приоритет у university_other)
# TODO: where_did_you_learn , если есть с суффиксом _other, то убедиться, что в where_did_you_learn другое? выставить самим
# FIXME: тест на создание нового универа, т.к. уже было падение по этой причине
from datetime import timedelta

import pytest

from admission.tests.factories import CampaignFactory, ApplicantFactory, \
    UniversityFactory
from admission.views import SESSION_LOGIN_KEY
from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from learning.settings import Branches


@pytest.mark.django_db
def test_application_form_inactive_or_past_campaign(client):
    create_url = reverse("public-api:v2:applicant_create")
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    campaign = CampaignFactory(current=True, branch__code=Branches.SPB,
                               application_starts_at=today - timedelta(days=2),
                               application_ends_at=today + timedelta(days=2))
    form_data = {
        "campaign": campaign.id
    }
    response = client.post(create_url, form_data)
    assert response.status_code == 400
    assert "campaign" not in response.data
    campaign.application_ends_at = today - timedelta(days=1)
    campaign.save()
    response = client.post(create_url, form_data)
    assert response.status_code == 400
    assert "campaign" in response.data


@pytest.mark.django_db
def test_application_form_preferred_study_programs(client):
    """`preferred_study_programs` is mandatory for on-campus branches"""
    url = reverse("public-api:v2:applicant_create")
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    campaign = CampaignFactory(current=True, branch__code=Branches.SPB,
                               application_starts_at=today - timedelta(days=2),
                               application_ends_at=today + timedelta(days=2))
    university = UniversityFactory()
    form_data = ApplicantFactory.build_application_form(
        campaign=campaign,
        university=university)
    if "preferred_study_programs" in form_data:
        del form_data["preferred_study_programs"]
    # preferred_study_programs are not specified for the distance branch
    assert campaign.branch.code != Branches.DISTANCE
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
    url = reverse("public-api:v2:applicant_create")
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    branch = BranchFactory(code=Branches.DISTANCE, city=None)
    campaign = CampaignFactory(current=True,
                               branch=branch,
                               application_starts_at=today - timedelta(days=2),
                               application_ends_at=today + timedelta(days=2))
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
