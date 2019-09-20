import datetime

import pytest
from django.utils import timezone

from projects.constants import EDITING_REPORT_COMMENT_AVAIL
from projects.tests.factories import ProjectReviewerFactory, \
    ReportCommentFactory
from users.constants import Roles
from users.models import User
from users.tests.factories import UserFactory, CuratorFactory


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


@pytest.mark.django_db
def test_update_report_comment():
    user = UserFactory()
    assert not user.has_perm("projects.change_reportcomment")
    created = timezone.now()
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    comment = ReportCommentFactory(author=reviewer1, created=created)
    assert reviewer1.has_perm("projects.change_own_reportcomment", comment)
    assert not reviewer1.has_perm("projects.change_reportcomment")
    assert not reviewer2.has_perm("projects.change_own_reportcomment", comment)
    comment.created = created - datetime.timedelta(seconds=EDITING_REPORT_COMMENT_AVAIL + 100)
    comment.save()
    assert not reviewer1.has_perm("projects.change_own_reportcomment", comment)
    curator = CuratorFactory()
    assert not curator.has_perm("projects.change_reportcomment")
    curator = CuratorFactory(groups=[Roles.CURATOR_PROJECTS])
    assert curator.has_perm("projects.change_reportcomment")
