from datetime import date

import pytest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.utils.timezone import now

from admission.models import Contest, Applicant, CampaignCity
from admission.tests.factories import CampaignFactory, ContestFactory
from core.models import University
from core.tests.factories import BranchFactory
from core.urls import reverse
from learning.settings import AcademicDegreeLevels
from universities.tests.factories import UniversityFactory

from .fields import AliasedChoiceField
from .serializers import ApplicantYandexFormSerializer, ApplicationYDSFormSerializer, UniversityCitySerializer

post_data = {
    "jsonrpc": "2.0",
    "method": "admission:form.add",
    "id": "21067737",
    "params": {
        "id": "473801197",
        "SecretToken": "",
        "yandex_login": "rochon",
        "last_name": "Иванов",
        "first_name": "Сергей",
        "patronymic": "Викторович",
        "email": "sergey.zherevchuk@jetbrains.com",
        "phone": "+7 91233456789",
        "living_place": "Санкт-Петербург",
        "birth_date": "1988-11-19",
        "branch": "Заочное отделение",
        "university": "Другое",
        "university_other": "ЛИТМО",
        "is_studying": "Да",
        "level_of_education": "1 (магистратура)",
        "faculty": "ИФФ",
        "year_of_graduation": "2012",
        "where_did_you_learn_other": "Интернет",
        "scientific_work": "Не было",
        "programming_experience": "-",
        "motivation": "Да я не поступаю, если честно...",
        "ml_experience": "Не изучал",
        "shad_plus_rash": "Да",
        "new_track": "Да",
        "new_track_scientific_articles": "У меня нет научных статей.",
        "new_track_projects": "Есть ли у вас открытые проекты вашего авторства, или в которых вы участвовали в составе команды, на github или на каком-либо из подобных сервисов? Если да, дайте ссылки на них.\r\n\r\nЕсть ли у вас открытые проекты вашего авторства, или в которых вы участвовали в составе команды, на github или на каком-либо из подобных сервисов? Если да, дайте ссылки на них.",
        "new_track_tech_articles": "Есть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.\r\n\r\nЕсть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.\r\n\r\nЕсть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.\r\n\r\nЕсть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.\r\n\r\nЕсть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.",
        "new_track_project_details": "Расскажите более подробно о каком-нибудь из своих проектов. Что хотелось сделать? Какие нетривиальные технические решения вы использовали? В чём были трудности и как вы их преодолевали? Пожалуйста, сохраните свой ответ в файле .pdf, выложите его на Яндекс.Диск и поместите сюда ссылку. Если у вас уже есть статья на эту тему и вы давали на неё ссылку в предыдущем вопросе, то можете поставить здесь прочерк.\r\n\r\nhttps://ya.ru/"
    },
}


def test_aliased_choices_field():
    field = AliasedChoiceField(
        allow_blank=True,
        choices=[
            ('one', 1, 'One'),
            ('two', 2, 'Two'),
        ]
    )
    assert field.run_validation('') == ''
    assert field.run_validation('one') == 1
    with pytest.raises(ValidationError):
        field.run_validation('three')
    assert field.to_representation(1) == 'one'


def test_aliased_choices_field_with_serializer():
    class TestSerializer(serializers.Serializer):
        field = AliasedChoiceField(
            choices=[
                ('one', 1, 'One'),
                ('two', 2, 'Two'),
            ]
        )

    s = TestSerializer(data={'field': 'one'})
    assert s.is_valid()
    assert s.validated_data == {'field': 1}
    assert not TestSerializer(data={'field': 'three'}).is_valid()


@pytest.mark.django_db
def test_admission_application_form_auth_token(settings, client):
    auth_token = settings.APPLICATION_FORM_SECRET_TOKEN = 'AAA'
    url = reverse("admission_application_form_new_task")
    response = client.get(url)
    assert response.status_code == 405  # Method not allowed
    response = client.get(url, HTTP_SecretToken=auth_token)
    assert response.status_code == 405
    response = client.post(url, HTTP_SecretToken=auth_token)
    assert response.status_code == 400  # Bad Request
    response = client.post(url, data={"jsonrpc": "2.0", "params": {"SecretToken": auth_token}},
                           content_type="application/json")
    assert response.status_code == 400  # Bad request


@pytest.mark.django_db
def test_admission_application_form_post(settings, client, mocker):
    settings.LANGUAGE_CODE = 'ru'
    mocked_task = mocker.patch('lk_yandexdataschool_ru.apps.application.tasks.register_new_application_form.delay')

    class Job:
        id = 42

    mocked_task.return_value = Job()
    auth_token = settings.APPLICATION_FORM_SECRET_TOKEN = 'AAA'
    url = reverse("admission_application_form_new_task")
    post_data = {
        "jsonrpc": "2.0",
        "method": "admission:form.add",
        "id": "42",
        "params": {
            'id': '33',
            'SecretToken': auth_token,
        },
    }
    response = client.post(url, data=post_data, content_type="application/json")
    assert response.status_code == 201
    mocked_task.assert_called_once_with(answer_id="33", language_code="ru", form_data={'id': '33'})


@pytest.mark.django_db
def test_applicant_form_serializer(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**post_data['params']}
    data['university'] = 'Другое'
    serializer = ApplicantYandexFormSerializer(data=data)
    is_valid = serializer.is_valid(raise_exception=False)
    assert not is_valid
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    university, _ = University.objects.update_or_create(pk=1, defaults={"name": data['university']})
    serializer = ApplicantYandexFormSerializer(data=data)
    serializer.is_valid(raise_exception=False)
    assert not serializer.errors
    instance = serializer.save()
    assert serializer.fields['scientific_work'].label in instance.experience
    assert data['scientific_work'] in instance.experience
    assert serializer.fields['programming_experience'].label in instance.experience
    assert data['programming_experience'] in instance.experience
    assert date(year=1988, month=11, day=19) == instance.birth_date
    assert instance.is_studying
    one2one = ['first_name', 'last_name', 'patronymic', 'email', 'phone', 'living_place',
               'motivation', 'university_other', 'faculty', 'where_did_you_learn_other', 'yandex_login']
    for field_name in one2one:
        assert data[field_name] == getattr(instance, field_name)
    assert instance.level_of_education == AcademicDegreeLevels.MASTER_1
    assert instance.year_of_graduation == 2012
    assert serializer.fields['new_track_scientific_articles'].label in instance.additional_info
    assert data['new_track_scientific_articles'] in instance.additional_info


@pytest.mark.django_db
def test_applicant_form_serializer_min_fields(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    branch = BranchFactory(code='msk', name='Москва', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    university, _ = University.objects.update_or_create(pk=1, defaults={"name": 'Другое'})
    data = {
        'id': '504733988',
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'patronymic': 'Иванович',
        'email': 'example@jetbrains.com',
        'phone': '+7 323 987-23-62',
        'birth_date': '2021-03-10',
        'living_place': 'Санкт-Петербург',
        'branch': branch.name,
        'university': university.name,
        'is_studying': 'Нет',
        'faculty': 'ИФФ',
        'year_of_graduation': '2012',
        'where_did_you_learn_other': '',
        'scientific_work': '',
        'programming_experience': '',
        'motivation': 'Зачем.',
        'ml_experience': 'Зачем.',
        # 'new_track_scientific_articles': '', 'new_track_projects': '', 'new_track_tech_articles': '',
        'new_track_project_details': '',
        'yandex_login': 'test'
    }
    serializer = ApplicantYandexFormSerializer(data=data)
    serializer.is_valid(raise_exception=False)
    assert not serializer.errors
    instance = serializer.save()
    assert instance.level_of_education is None
    assert serializer.fields['new_track_scientific_articles'].label not in instance.additional_info


@pytest.mark.django_db
def test_applicant_form_serializer_save_new_track_fields(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    branch = BranchFactory(code='msk', name='Москва', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    university, _ = University.objects.update_or_create(pk=1, defaults={"name": 'Другое'})
    data = {
        'id': '112326498',
        'last_name': 'Иванова',
        'first_name': 'Мария',
        'patronymic': 'Ивановна',
        'email': 'example@yandex.ru',
        'phone': '+7 977 123-45-67',
        'birth_date': '2021-03-01',
        'living_place': 'Воркута, Республика Коми, Россия',
        'branch': 'Москва',
        'university': 'Другое',
        'university_other': 'Государственный левополушарный',
        'is_studying': 'Да',
        'level_of_education': 'Другое',
        'faculty': 'кафедра Смеха Сквозь Слезы',
        'year_of_graduation': '2222',
        'where_did_you_learn_other': 'в клубе анонимных нытиков',
        'scientific_work': '',
        'programming_experience': '',
        'motivation': 'привлекает бесплатная еда',
        'ml_experience': 'иногда училась в машине, да',
        'shad_plus_rash': 'Нет',
        'new_track': 'Да',
        'new_track_scientific_articles': 'несколько в кул гёрл, найду, пришлю',
        'yandex_login': 'test'
    }
    serializer = ApplicantYandexFormSerializer(data=data)
    serializer.is_valid(raise_exception=False)
    assert not serializer.errors
    instance = serializer.save()


yds_post_data = {
    "last_name": "Иванов",
    "first_name": "Иван",
    "patronymic": "Иванович",
    "yandex_login": "ivanov",
    "telegram_username": "pavel_durov",
    "email": "somemail@mail.com",
    "phone": "89991234567",
    "birth_date": "2000-01-01",
    "living_place": "Санкт-Петербург",
    "faculty": "Факультет",
    "is_studying": False,
    "year_of_graduation": "2022",
    "where_did_you_learn": ["friends", "other"],
    "motivation": "Зачем вы поступаете в ШАД?",
    "ml_experience": "Изучали ли вы раньше машинное обучение/анализ данных?",
    "campaign": None,
    "new_track": True,
    "shad_agreement": True,
    "rash_agreement": False,
    "ticket_access": True,
    "email_subscription": True,
    "university": None,
    "partner": None,
    "university_city": {"is_exists": False, "city_name": "Петергоф"}
}


@pytest.mark.django_db
def test_application_YDS_form_serializer(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**yds_post_data}
    university = UniversityFactory()
    data['university'] = university.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid(raise_exception=False)
    branch = BranchFactory(code='msk', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk
    data.update({
        'new_track': True,
        'new_track_project_details': "new_track_project_details",
        'new_track_projects': 'new_track_projects',
        'new_track_scientific_articles': 'new_track_scientific_articles',
        'new_track_tech_articles': 'new_track_tech_articles',
        'shad_plus_rash': True,
        'rash_agreement': True,
        'is_studying': True,
        'level_of_education': AcademicDegreeLevels.MASTER_1,
        'where_did_you_learn': ['friends'],
    })
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)
    assert not serializer.errors
    instance = serializer.save()
    assert instance.campaign == campaign
    assert date(year=2000, month=1, day=1) == instance.birth_date
    assert instance.is_studying
    assert instance.level_of_education == AcademicDegreeLevels.MASTER_1
    one2one = ['first_name', 'last_name', 'patronymic', 'email', 'phone', 'living_place',
               'motivation', 'faculty', 'yandex_login']
    for field_name in one2one:
        assert data[field_name] == getattr(instance, field_name)
    assert instance.year_of_graduation == int(data['year_of_graduation'])
    assert instance.experience == data['ml_experience']
    assert instance.data == {
        "utm": {},
        'yandex_profile': {},
        "shad_agreement": True,
        "ticket_access": True,
        "email_subscription": True,
        "university_city": data["university_city"],
        "data_format_version": '0.6',
        'new_track': True,
        'new_track_project_details': "new_track_project_details",
        'new_track_projects': "new_track_projects",
        'new_track_scientific_articles': "new_track_scientific_articles",
        'new_track_tech_articles': "new_track_tech_articles"
    }


@pytest.mark.django_db
def test_application_YDS_form_serializer_min_fields(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**yds_post_data}
    university = UniversityFactory()
    data['university'] = university.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid(raise_exception=False)
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)
    assert not serializer.errors
    instance = serializer.save()
    assert instance.campaign == campaign
    assert date(year=2000, month=1, day=1) == instance.birth_date
    assert not instance.is_studying
    one2one = ['first_name', 'last_name', 'patronymic', 'email', 'phone', 'living_place',
               'motivation', 'faculty', 'yandex_login']
    for field_name in one2one:
        assert data[field_name] == getattr(instance, field_name)
    assert instance.year_of_graduation == int(data['year_of_graduation'])
    assert instance.experience == data['ml_experience']
    assert instance.data == {
        "utm": {},
        'yandex_profile': {},
        "shad_agreement": True,
        "ticket_access": True,
        "university_city": data["university_city"],
        "email_subscription": True,
        "data_format_version": '0.6',
        'new_track': True,
        'new_track_project_details': None,
        'new_track_projects': None,
        'new_track_scientific_articles': None,
        'new_track_tech_articles': None,
    }


@pytest.mark.django_db
def test_application_YDS_form_serializer_msk_required_fields(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**yds_post_data}
    university = UniversityFactory()
    data['university'] = university.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid(raise_exception=False)
    branch = BranchFactory(code='msk', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk

    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid()


@pytest.mark.django_db
def test_application_YDS_form_serializer_university_field(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**yds_post_data}
    university = UniversityFactory()
    data['university'] = university.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid(raise_exception=False)
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk

    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid()

    del data['university']
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid()

    data['university_other'] = 'Петергофское тех. училище'
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid()


@pytest.mark.django_db
def test_university_city_serializer(settings, mocker):
    serializer = UniversityCitySerializer(data={})
    assert not serializer.is_valid()

    serializer = UniversityCitySerializer(data={"is_exists": True})
    assert not serializer.is_valid()
    assert "pk" in serializer.errors

    serializer = UniversityCitySerializer(data={"is_exists": True, "pk": 1})
    assert serializer.is_valid()

    serializer = UniversityCitySerializer(data={"is_exists": False})
    assert not serializer.is_valid()
    assert "city_name" in serializer.errors

    serializer = UniversityCitySerializer(data={"is_exists": False, "city_name": "Петергоф"})
    assert serializer.is_valid()


@pytest.mark.django_db
def test_application_YDS_form_serializer_university_city_field(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**yds_post_data}
    university = UniversityFactory()
    data['university'] = university.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid(raise_exception=False)
    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk

    del data['university_city']
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid()

    data['university_city'] = dict()
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid()

    data['university_city'] = {"is_exists": False, "city_name": "Петергоф"}
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)

    data['university_city'] = {"is_exists": True, "pk": 1}
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid()


@pytest.mark.django_db
def test_application_YDS_form_creates(settings, client):
    data = {**yds_post_data}
    university = UniversityFactory()
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
    response = client.post(url, data=data, content_type='application/json')
    assert response.status_code == 201
    assert Applicant.objects.exists()


@pytest.mark.django_db
def test_application_YDS_form_serializer_test_utm(settings, mocker):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    data = {**yds_post_data}
    university = UniversityFactory()
    data['university'] = university.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert not serializer.is_valid(raise_exception=False)

    branch = BranchFactory(code='distance', site_id=settings.SITE_ID)
    campaign = CampaignFactory(branch=branch, year=now().year, current=True)
    CampaignCity.objects.create(campaign=campaign, city=None)
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    data['campaign'] = campaign.pk
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)
    assert not serializer.errors
    instance = serializer.save()
    assert instance.data['utm'] == {}

    data['email'] = "abc@def.ghi"
    data['utm'] = {
        "utm_source": "source",
        "utm_medium": "medium",
        "utm_campaign": "campaign",
        "utm_term": "term",
        "utm_content": "content"
    }
    serializer = ApplicationYDSFormSerializer(data=data)
    assert serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    assert instance.data["utm"] == data['utm']
