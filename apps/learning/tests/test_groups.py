import pytest

from learning.permissions import has_master_degree
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import User
from users.tests.factories import StudentFactory


@pytest.mark.django_db
def test_user_permissions():
    """
    Tests properties based on groups:
        * is_student
        * is_volunteer
        * is_graduate
        * is_teacher
    """
    user = User(username="foo", email="foo@localhost.ru")
    user.save()
    assert not user.is_student
    assert not user.is_volunteer
    assert not user.is_teacher
    assert not user.is_graduate
    user = User(username="bar", email="bar@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    assert user.is_student
    assert not user.is_volunteer
    assert not user.is_teacher
    assert not user.is_graduate
    user = User(username="baz", email="baz@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    user.add_group(Roles.TEACHER)
    assert user.is_student
    assert not user.is_volunteer
    assert user.is_teacher
    assert not user.is_graduate
    user = User(username="baq", email="baq@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    user.add_group(Roles.TEACHER)
    user.add_group(Roles.GRADUATE)
    assert user.is_student
    assert not user.is_volunteer
    assert user.is_teacher
    assert user.is_graduate
    user = User(username="zoo", email="zoo@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    user.add_group(Roles.TEACHER)
    user.add_group(Roles.GRADUATE)
    user.add_group(Roles.VOLUNTEER)
    assert user.is_student
    assert user.is_volunteer
    assert user.is_teacher
    assert user.is_graduate


@pytest.mark.django_db
def test_anonymous_user_permissions(client):
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert not request_user.is_authenticated
    assert not request_user.is_student
    assert not request_user.is_volunteer
    assert not has_master_degree(request_user)
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_interviewer


@pytest.mark.django_db
def test_request_user_permissions(client):
    # Active student
    student = StudentFactory(status='')
    client.login(student)
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert request_user.is_authenticated
    assert request_user.is_student
    assert not request_user.is_volunteer
    assert request_user.is_active_student
    assert not has_master_degree(request_user)
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_interviewer
    # Expelled student
    student.status = StudentStatuses.EXPELLED
    student.save()
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert request_user.is_authenticated
    assert request_user.is_student
    assert not request_user.is_volunteer
    assert not request_user.is_active_student
    assert not has_master_degree(request_user)
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_interviewer