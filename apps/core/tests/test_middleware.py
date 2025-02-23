import pytest
from apps.core.middleware import UserStatusCheckMiddleware
from apps.learning.settings import StudentStatuses
from apps.users.tests.factories import StudentFactory
from compscicenter_ru.apps.application.views import SESSION_LOGIN_KEY

@pytest.fixture
def middleware():
    return UserStatusCheckMiddleware(get_response=lambda req: 'response')

@pytest.fixture
def request_with_user():
    class Request:
        def __init__(self):
            self.user = StudentFactory(email='bounce@simulator.amazonses.com')
            self.session = {}
    return Request()


@pytest.mark.django_db
@pytest.mark.parametrize("status", [
    StudentStatuses.EXPELLED,
    StudentStatuses.ACADEMIC_LEAVE,
    StudentStatuses.ACADEMIC_LEAVE_SECOND
])
def test_call_with_inactive_student(middleware, request_with_user, settings, status):

    request_with_user.session[SESSION_LOGIN_KEY] = 'some_value'
    student_profile = request_with_user.user.get_student_profile(settings.SITE_ID)
    student_profile.status = status

    response = middleware(request_with_user)

    assert SESSION_LOGIN_KEY not in request_with_user.session
    assert response == 'response'

@pytest.mark.django_db
@pytest.mark.parametrize("status", [
    StudentStatuses.REINSTATED,
    StudentStatuses.WILL_GRADUATE,
    StudentStatuses.GRADUATE
])
def test_call_with_active_student(middleware, request_with_user, settings, status):

    request_with_user.session[SESSION_LOGIN_KEY] = 'some_value'
    student_profile = request_with_user.user.get_student_profile(settings.SITE_ID)
    student_profile.status = status

    response = middleware(request_with_user)

    assert SESSION_LOGIN_KEY in request_with_user.session
    assert response == 'response'


@pytest.mark.django_db
def test_call_without_student_profile(middleware, request_with_user, mocker):

    mock_get_student = mocker.patch("users.services.get_student_profile")
    mock_get_student.return_value = None
    request_with_user.session[SESSION_LOGIN_KEY] = 'some_value'

    response = middleware(request_with_user)

    assert SESSION_LOGIN_KEY in request_with_user.session
    assert response == 'response'
