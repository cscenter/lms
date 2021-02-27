import json
from datetime import date
from unittest.mock import MagicMock

import pytest
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from admission.models import Contest
from admission.tests.factories import CampaignFactory, ContestFactory
from core.models import University
from core.tests.factories import BranchFactory, UniversityFactory
from core.urls import reverse
from learning.settings import AcademicDegreeLevels
from .fields import AliasedChoiceField
from .serializers import ApplicantYandexFormSerializer

post_data = {
  "jsonrpc": "2.0",
  "method": "admission:form.add",
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
  "id": "21067737"
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

