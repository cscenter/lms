import pytest

from users.constants import AcademicRoles
from users.models import User


@pytest.mark.django_db
def test_user_permissions():
    """
    Tests properties based on groups:
        * is_curator_of_projects
        * is_project_reviewer
    """
    user = User(username="foo", email="foo@localhost.ru")
    user.save()
    assert not user.is_curator_of_projects
    assert not user.is_project_reviewer
    user = User(username="bar", email="bar@localhost.ru")
    user.save()
    user.add_group(AcademicRoles.CURATOR_PROJECTS)
    assert user.is_curator_of_projects
    assert not user.is_project_reviewer
    user = User(username="baz", email="baz@localhost.ru")
    user.save()
    user.add_group(AcademicRoles.PROJECT_REVIEWER)
    user.add_group(AcademicRoles.CURATOR_PROJECTS)
    assert user.is_curator_of_projects
    assert user.is_project_reviewer


@pytest.mark.django_db
def test_anonymous_user_permissions(client):
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert not request_user.is_authenticated
    assert not request_user.is_curator_of_projects
    assert not request_user.is_project_reviewer
