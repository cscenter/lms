from datetime import datetime

import pytest
import pytz

from core.tests.factories import BranchFactory
from learning.settings import Branches
from surveys.constants import STATUS_PUBLISHED
from surveys.tests.factories import CourseSurveyFactory


@pytest.mark.django_db
def test_course_survey_detail_deadline(client, mocker, settings):
    settings.language = 'en'
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    msk_tz = pytz.timezone("Europe/Moscow")
    nsk_tz = pytz.timezone("Asia/Novosibirsk")
    mocked_timezone.return_value = nsk_tz.localize(datetime(2018, 4, 1, 12, 0))
    expire_at = nsk_tz.localize(datetime(2018, 4, 1, 13, 42))
    branch_nsk = BranchFactory(code=Branches.SPB)
    course_survey = CourseSurveyFactory(course__branch=branch_nsk,
                                        expire_at=expire_at)
    url = course_survey.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 404
    course_survey.form.status = STATUS_PUBLISHED
    course_survey.form.save()
    response = client.get(url)
    assert response.status_code == 200
    deadline = response.context_data["survey_deadline"]
    assert expire_at.astimezone(msk_tz).strftime("%H:%M") in deadline
