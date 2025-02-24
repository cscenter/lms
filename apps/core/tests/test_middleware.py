import pytest
from apps.learning.settings import StudentStatuses
from apps.users.tests.factories import StudentFactory, UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize("status", [
    StudentStatuses.EXPELLED,
    StudentStatuses.ACADEMIC_LEAVE,
    StudentStatuses.ACADEMIC_LEAVE_SECOND
])
def test_call_with_inactive_student(client, settings, status):
    student = StudentFactory()
    student_profile = student.get_student_profile(settings.SITE_ID)
    student_profile.status = status
    student_profile.save()
    client.login(student)

    response = client.get('/')
    assert not response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
@pytest.mark.parametrize("status", [
    StudentStatuses.REINSTATED,
    StudentStatuses.WILL_GRADUATE,
    StudentStatuses.GRADUATE
])
def test_call_with_active_student(client, settings, status):

    student = StudentFactory()
    student_profile = student.get_student_profile(settings.SITE_ID)
    student_profile.status = status
    student_profile.save()
    client.login(student)

    response = client.get('/')
    assert response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_call_without_student_profile(client):

    student = UserFactory()
    client.login(student)

    response = client.get('/')
    assert response.wsgi_request.user.is_authenticated
