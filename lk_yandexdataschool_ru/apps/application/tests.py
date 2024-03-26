import json
import tempfile

from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.timezone import now

import pytest
from django.conf import settings

from admission.models import Contest, Applicant, CampaignCity
from admission.tests.factories import CampaignFactory, ContestFactory
from core.tests.factories import BranchFactory
from core.urls import reverse
from universities.tests.factories import UniversityFactory, CityFactory

yds_post_data = {
    'last_name': 'Фамилия',
    'first_name': 'Имя',
    'patronymic': 'Отчество',
    'yandex_login': 'test',
    'birth_date': '2000-01-01',
    'gender': 'M',
    'email': 'mail@mail.com',
    'phone': '+1234567890',
    'telegram_username': 'telegram',
    'residence_city': None,
    "living_place": "Минск",
    'has_diploma': 'yes',
    'diploma_degree': '1',
    'faculty': 'Факультет',
    'year_of_graduation': '2024',
    'new_track': False,
    'partner': None,
    'has_internship': True,
    'internship_workplace': 'Место стажирровки',
    'internship_position': 'Стажер',
    'internship_beginning': '1999-10-10',
    'internship_not_ended': True,
    'internship_end': None,
    'has_job': True,
    'workplace': 'Место работы',
    'position': 'Обязанности',
    'working_hours': '40',
    'where_did_you_learn': ['group', 'post', 'mailing', 'community', 'bloger', 'other'],
    'where_did_you_learn_other': 'Мой вариант',
    'motivation': 'Мотивация',
    'ml_experience': 'Опыт в МЛ',
    'additional_info': 'Дополнительная информация',
    'utm': {'utm_campaign': None, 'utm_content': None, 'utm_medium': None, 'utm_source': None, 'utm_term': None},
    'shad_agreement': True,
    'ticket_access': False,
    'honesty': True,
    'mail_allowance': True,
    'awareness': True,
    'email_subscription': False
}


def make_post_data(payload):
    json_string = json.dumps(payload)
    temp_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    temp_file.write(json_string.encode('utf-8'))
    temp_file.seek(0)
    uploaded_payload = InMemoryUploadedFile(
        file=temp_file,
        field_name='payload',
        name='payload.json',
        content_type='application/json',
        size=len(json_string),
        charset='utf-8'
    )
    image = Image.new('RGB', (100, 100), color='red')
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file, format='JPEG')
    temp_file.seek(0)
    uploaded_file = InMemoryUploadedFile(
        file=temp_file,
        field_name='photo',
        name='photo.jpg',
        content_type='image/jpeg',
        size=image.__sizeof__(),
        charset='utf-8'
    )
    return {
        "photo": uploaded_file,
        "payload": uploaded_payload
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
    CampaignCity.objects.create(campaign=campaign)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    university = UniversityFactory()
    university_city = CityFactory()
    data = {**yds_post_data}
    data['university'] = university.pk
    data['university_city'] = {'is_exists': True, 'pk': university_city.pk}
    data['campaign'] = campaign.pk

    url = reverse('application_form')
    response = client.get(url)
    assert response.status_code == 200
    assert response.context_data["show_form"]
    context = response.context_data["app"]["props"]
    assert len(context["alwaysAllowCampaigns"]) == 1
    assert campaign.pk in map(lambda c: c["campaign_id"], context["alwaysAllowCampaigns"])

    url = reverse('applicant_create')
    session = client.session
    session["application_ya_login"] = data['yandex_login']
    session.save()
    response = client.post(url, data=make_post_data(data))
    assert response.status_code == 201


@pytest.mark.django_db
def test_view_application_form_msk_campaigns(client):
    distance_branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    msk_branch = BranchFactory(code='msk', site_id=settings.SITE_ID)
    msk_campaign = CampaignFactory(branch=msk_branch, year=now().year, current=True)
    distance_campaign = CampaignFactory(branch=distance_branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=msk_campaign)
    CampaignCity.objects.create(campaign=distance_campaign)
    contest = ContestFactory(campaign=msk_campaign, type=Contest.TYPE_TEST)
    university = UniversityFactory()
    university_city = CityFactory()
    data = {**yds_post_data}

    url = reverse('application_form')
    response = client.get(url)
    assert response.status_code == 200
    assert response.context_data["show_form"]
    context = response.context_data["app"]["props"]
    assert len(context["alwaysAllowCampaigns"]) == 2
    campaigns_pk = map(lambda c: c["campaign_id"], context["alwaysAllowCampaigns"])
    assert {msk_campaign.pk, distance_campaign.pk} == set(campaigns_pk)

    data['university'] = university.pk
    data['university_city'] = {'is_exists': True, 'pk': university_city.pk}
    data['campaign'] = msk_campaign.pk
    data['new_track'] = True
    url = reverse('applicant_create')
    session = client.session
    session["application_ya_login"] = data['yandex_login']
    session.save()
    response = client.post(url, data=make_post_data(data))
    assert response.status_code == 201
    assert Applicant.objects.exists()


@pytest.mark.django_db
def test_application_YDS_form_creates(settings, client):
    data = {**yds_post_data}
    university = UniversityFactory()
    university_city = CityFactory()
    data['university_city'] = {'is_exists': True, 'pk': university_city.pk}
    data['university'] = university.pk
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk
    url = reverse('applicant_create')
    session = client.session
    session["application_ya_login"] = data['yandex_login']
    session.save()
    response = client.post(url, data=make_post_data(data))
    assert response.status_code == 201
    assert Applicant.objects.exists()


@pytest.mark.django_db
def test_valid_data_YDS_form(settings, client):
    data = {**yds_post_data}
    university = UniversityFactory()
    university_city = CityFactory()
    data['university_city'] = {'is_exists': True, 'pk': university_city.pk}
    data['university'] = university.pk
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk
    url = reverse('applicant_create')
    session = client.session
    session["application_ya_login"] = data['yandex_login']
    session.save()
    response = client.post(url, data=make_post_data(data))
    assert response.status_code == 201
    assert Applicant.objects.exists()
    session["application_ya_login"] = data['yandex_login']
    session.save()
    data['email'] = 'incorrect@mail@gmail.com'
    data['telegram_username'] = 'https://t.me/username'
    data['birth_date'] = '0900-01-01'
    data['internship_beginning'] = '0900-01-01'
    data['phone'] = '+12 345-678-90'
    response = client.post(url, data=make_post_data(data))
    assert response.status_code == 400
    assert json.loads(response.content.decode()) == \
           {
               "birth_date": ["Ensure this value is greater than or equal to 1900-01-01."],
               "email": ["Enter a valid email address."],
               "phone": ["Enter a valid value."],
               "telegram_username": [
                   "Telegram username may only contain 5-32 alphanumeric characters or single underscores."
                   " Should begin only with letter and end with alphanumeric."],
               "internship_beginning": ["Ensure this value is greater than or equal to 1900-01-01."]}
