from datetime import timedelta

import factory
import pytest
from django.db import models
from django.utils import timezone

from admission.tests.factories import CampaignFactory, ApplicantFactory, \
    UniversityFactory
from application.api.serializers import ApplicationFormSerializer
from application.views import SESSION_LOGIN_KEY
from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from learning.settings import Branches


def build_application_form(**kwargs):
    form_data = factory.build(dict, FACTORY_CLASS=ApplicantFactory, **kwargs)
    for k in list(form_data.keys()):
        if k not in ApplicationFormSerializer.Meta.fields:
            del form_data[k]
        elif isinstance(form_data[k], models.Model):
            if form_data[k].pk is None:
                del form_data[k]
            else:
                form_data[k] = form_data[k].pk
    return form_data


@pytest.mark.django_db
def test_application_form_availability(client):
    today = timezone.now()
    campaign = CampaignFactory(year=today.year, current=True)
    url = reverse("application:form")
    response = client.get(url)
    assert response.status_code == 200
    campaign.current = False
    campaign.save()
    response = client.get(url)
    assert response.status_code == 200
    assert not response.context_data["show_form"]
    campaign.current = True
    campaign.application_ends_at = today - timedelta(days=1)
    campaign.save()
    response = client.get(url)
    assert not response.context_data["show_form"]


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
    form_data = build_application_form(campaign=campaign, university=university)
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
    form_data = build_application_form(campaign=campaign, university=university)
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
