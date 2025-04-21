from datetime import datetime

import pytest
import pytz

from core.tests.factories import BranchFactory
from learning.settings import Branches
from surveys.constants import STATUS_PUBLISHED
from surveys.tests.factories import CourseSurveyFactory
from django.http import HttpRequest

from surveys.views import ReportBugView, ReportIdeaView
from users.models import ExtendedAnonymousUser
from users.tests.factories import CuratorFactory, StudentFactory


@pytest.mark.django_db
def test_course_survey_detail_deadline(client, mocker, settings):
    settings.language = 'en'
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    msk_tz = pytz.timezone("Europe/Moscow")
    nsk_tz = pytz.timezone("Asia/Novosibirsk")
    mocked_timezone.return_value = nsk_tz.localize(datetime(2018, 4, 1, 12, 0))
    expire_at = nsk_tz.localize(datetime(2018, 4, 1, 13, 42))
    branch_nsk = BranchFactory(code=Branches.SPB)
    course_survey = CourseSurveyFactory(course__main_branch=branch_nsk,
                                        expire_at=expire_at)
    url = course_survey.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 404
    course_survey.form.status = STATUS_PUBLISHED
    course_survey.form.save()
    response = client.get(url)
    assert response.status_code == 200
    deadline = response.context_data["survey_deadline"]
    hour = int(expire_at.astimezone(msk_tz).strftime("%H"))
    minutes = int(expire_at.astimezone(msk_tz).strftime("%M"))
    assert f"{hour}:{minutes}" in deadline

@pytest.mark.django_db
@pytest.mark.parametrize("user_factory, view_class, expected_url", [
    (StudentFactory, ReportBugView, "https://forms.yandex.ru/surveys/13739605.ea35e390cf310d138e5e32315ecb2c07f1813e89/"),
    (StudentFactory, ReportIdeaView, "https://forms.yandex.ru/surveys/13739606.3c14ec2d9997b34e4b254c8abddf1636af04f78f/"),
    (CuratorFactory, ReportBugView, "https://forms.yandex.ru/surveys/13739605.ea35e390cf310d138e5e32315ecb2c07f1813e89/"),
    (CuratorFactory, ReportIdeaView, "https://forms.yandex.ru/surveys/13739606.3c14ec2d9997b34e4b254c8abddf1636af04f78f/"),
    (None, ReportBugView, "https://forms.yandex.ru/surveys/13739605.ea35e390cf310d138e5e32315ecb2c07f1813e89/"),
    (None , ReportIdeaView, "https://forms.yandex.ru/surveys/13739606.3c14ec2d9997b34e4b254c8abddf1636af04f78f/")
])
def test_report_views_direct(mocker, user_factory, view_class, expected_url):
    """Test that report views work correctly for different user types."""
    # Mock the logger
    mock_logger = mocker.patch('surveys.views.logger')
    
    user = user_factory() if user_factory else ExtendedAnonymousUser()
    
    request = mocker.Mock(spec=HttpRequest)
    request.user = user
    request.META = {
        'HTTP_REFERER': 'http://testserver/student-page/',
        'HTTP_USER_AGENT': 'User Agent'
    }
    request.COOKIES = {'sessionid': 'student-session-id'}
    request.environ = {'HTTP_USER_AGENT': 'Student User Agent'}
    
    view = view_class()
    
    response = view.get(request)
    
    assert response.status_code == 302
    assert response.url == expected_url
    
    assert mock_logger.info.called
    log_message = mock_logger.info.call_args[0][0]
    
    assert str(user.pk) in log_message  # User ID should be in the log
    assert f"Got {view.prefix} report from" in log_message
