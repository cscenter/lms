from django.utils.timezone import now

import pytest
from django.conf import settings

from admission.models import Contest, Applicant
from admission.tests.factories import CampaignFactory, ContestFactory
from core.tests.factories import BranchFactory
from core.urls import reverse
from universities.tests.factories import UniversityFactory

yds_post_data = {
    "last_name": "Иванов",
    "first_name": "Иван",
    "patronymic": "Иванович",
    "yandex_login": "ivanov",
    "email": "somemail@mail.com",
    "phone": "89991234567",
    "birth_date": "2000-01-01",
    "living_place": "Санкт-Петербург",
    "faculty": "Факультет",
    "is_studying": False,
    "year_of_graduation": "2022",
    "motivation": "Зачем вы поступаете в ШАД?",
    "ml_experience": "Изучали ли вы раньше машинное обучение/анализ данных?",
    "campaign": None,
    "shad_agreement": True,
    "ticket_access": True,
    "email_subscription": True,
    "university": None,
    "new_track": True,
    "university_city": {"is_exists": False, "city_name": "Петергоф"},
    "where_did_you_learn": ["friends"],
}


@pytest.mark.django_db
def test_view_application_form_no_campaigns(client):
    url = reverse('application_form')
    response = client.get(url)
    assert response.status_code == 200
    assert not response.context_data["show_form"]


@pytest.mark.django_db
def test_view_application_form_no_msk_campaigns(client):
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    university = UniversityFactory()
    data = {**yds_post_data}
    data['university'] = university.pk
    data['campaign'] = campaign.pk

    url = reverse('application_form')
    response = client.get(url)
    assert response.status_code == 200
    assert response.context_data["show_form"]
    context = response.context_data["app"]["props"]
    assert len(context["campaigns"]) == 1
    assert campaign.pk in map(lambda c: c["id"], context["campaigns"])

    url = reverse('applicant_create')
    session = client.session
    session["application_ya_login"] = data['yandex_login']
    session.save()
    response = client.post(url, data=data, content_type='application/json')
    assert response.status_code == 201


@pytest.mark.django_db
def test_view_application_form_msk_campaigns(client):
    distance_branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    msk_branch = BranchFactory(code='msk', site_id=settings.SITE_ID)
    msk_campaign = CampaignFactory(branch=msk_branch, year=now().year, current=True)
    distance_campaign = CampaignFactory(branch=distance_branch, year=now().year, current=True)
    contest = ContestFactory(campaign=msk_campaign, type=Contest.TYPE_TEST)
    university = UniversityFactory()
    data = {**yds_post_data}

    url = reverse('application_form')
    response = client.get(url)
    assert response.status_code == 200
    assert response.context_data["show_form"]
    context = response.context_data["app"]["props"]
    assert len(context["campaigns"]) == 2
    campaigns_pk = map(lambda c: c["id"], context["campaigns"])
    assert {msk_campaign.pk, distance_campaign.pk} == set(campaigns_pk)

    data['university'] = university.pk
    data['campaign'] = msk_campaign.pk
    data['new_track'] = True
    url = reverse('applicant_create')
    session = client.session
    session["application_ya_login"] = data['yandex_login']
    session.save()
    response = client.post(url, data=data, content_type='application/json')
    assert response.status_code == 201
    assert Applicant.objects.exists()
