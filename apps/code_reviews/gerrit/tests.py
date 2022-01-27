from decimal import Decimal

import pytest
from rq.job import Job

from django.core.exceptions import ValidationError

from auth.mixins import RolePermissionRequiredMixin
from auth.tests.factories import ConnectedAuthServiceFactory
from code_reviews.gerrit.services import normalize_code_review_score
from code_reviews.gerrit.tasks import import_gerrit_code_review_score
from code_reviews.tests.factories import GerritChangeFactory
from core.urls import reverse
from courses.constants import AssignmentStatuses
from courses.tests.factories import AssignmentFactory
from learning.permissions import EditStudentAssignment
from users.tests.factories import CuratorFactory, TeacherFactory


@pytest.mark.django_db
def test_view_gerrit_webhook_comment_added_permissions(client, lms_resolver, settings, mocker):
    mocker.patch('code_reviews.gerrit.views.import_gerrit_code_review_score.delay',
                 return_value=Job(id=42, connection=object()))
    url = reverse('code_reviews:gerrit-hooks:comment-added', subdomain=settings.LMS_SUBDOMAIN)
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, RolePermissionRequiredMixin)
    assert resolver.func.view_class.permission_classes == [EditStudentAssignment]
    response = client.post(url)
    assert response.status_code == 401
    curator = CuratorFactory()
    # Token-based login required
    client.login(curator)
    response = client.post(url)
    assert response.status_code == 401
    auth_token = client.get_api_token(curator)
    response = client.post(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 400
    # Not enough permissions
    teacher = TeacherFactory()
    auth_token = client.get_api_token(teacher)
    response = client.post(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 403


@pytest.mark.django_db
def test_view_gerrit_webhook_comment_added(client, lms_resolver, settings, mocker):
    mocker.patch('code_reviews.gerrit.views.import_gerrit_code_review_score.delay',
                 return_value=Job(id=42, connection=object()))
    url = reverse('code_reviews:gerrit-hooks:comment-added', subdomain=settings.LMS_SUBDOMAIN)
    curator = CuratorFactory()
    auth_token = client.get_api_token(curator)
    payload = {
        'score_old': '0',
        'score_new': '0',
        'username': 'username',
        'change_id': 'change_id',
    }
    response = client.post(url, data=payload, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 201
    assert response.json()['id'] == 42


@pytest.mark.django_db
def test_services_normalize_code_review_score():
    assignment = AssignmentFactory(maximum_score=20)
    assert normalize_code_review_score(-1, assignment) == 0
    assert normalize_code_review_score(0, assignment) == 0
    assert normalize_code_review_score(1, assignment) == Decimal(10)
    assert normalize_code_review_score(2, assignment) == Decimal(20)
    assignment.maximum_score = 29
    assert normalize_code_review_score(1, assignment) == Decimal('14.5')


@pytest.mark.django_db
def test_task_import_gerrit_code_review_score(settings):
    gerrit_change = GerritChangeFactory()
    student_assignment = gerrit_change.student_assignment
    assert student_assignment.score is None
    assert student_assignment.status == AssignmentStatuses.NOT_SUBMITTED
    gerrit_auth = ConnectedAuthServiceFactory(provider='gerrit')
    # Score already set by someone and value differs from the previous update
    student_assignment.score = 0
    student_assignment.save()
    with pytest.raises(ValidationError):
        import_gerrit_code_review_score(change_id=gerrit_change.change_id,
                                        score_old=1,
                                        score_new=2,
                                        username=gerrit_auth.uid)
    # Gerrit user without permissions
    teacher = TeacherFactory()
    teacher_connected = ConnectedAuthServiceFactory(provider='gerrit', user=teacher)
    task_id = import_gerrit_code_review_score(change_id=gerrit_change.change_id,
                                              score_old=0,
                                              score_new=2,
                                              username=teacher_connected.uid)
    assert task_id is None
    student_assignment.refresh_from_db()
    assert student_assignment.score == 0
    course = student_assignment.assignment.course
    course.teachers.add(teacher)
    import_gerrit_code_review_score(change_id=gerrit_change.change_id,
                                    score_old=0,
                                    score_new=2,
                                    username=teacher_connected.uid)
    student_assignment.refresh_from_db()
    assert student_assignment.status == AssignmentStatuses.COMPLETED
    import_gerrit_code_review_score(change_id=gerrit_change.change_id,
                                    score_old=2,
                                    score_new=1,
                                    username=teacher_connected.uid)
    student_assignment.refresh_from_db()
    assert student_assignment.score == student_assignment.assignment.maximum_score // 2
    assert student_assignment.status == AssignmentStatuses.NEED_FIXES
