import pytest

from users.constants import Roles
from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_user_permissions():
    """
    Tests properties based on groups:
        * is_curator_of_projects
        * is_project_reviewer
    """
    user = UserFactory()
    user.save()
    assert not user.is_curator_of_projects
    assert not user.is_project_reviewer
    user = UserFactory()
    user.save()
    user.add_group(Roles.CURATOR_PROJECTS)
    assert user.is_curator_of_projects
    assert not user.is_project_reviewer
    user = UserFactory()
    user.save()
    user.add_group(Roles.PROJECT_REVIEWER)
    user.add_group(Roles.CURATOR_PROJECTS)
    assert user.is_curator_of_projects
    assert user.is_project_reviewer


@pytest.mark.django_db
def test_anonymous_user_permissions(client):
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert not request_user.is_authenticated
    assert not request_user.is_curator_of_projects
    assert not request_user.is_project_reviewer
