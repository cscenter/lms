from decimal import Decimal

import pytest

from django.conf import settings

from auth.mixins import RolePermissionRequiredMixin
from auth.permissions import perm_registry
from core.urls import reverse
from learning.permissions import EditStudentAssignment
from learning.services.personal_assignment_service import (
    update_personal_assignment_score
)
from learning.settings import AssignmentScoreUpdateSource
from learning.tests.factories import StudentAssignmentFactory
from users.tests.factories import CuratorFactory, UserFactory


@pytest.mark.django_db
def test_api_view_personal_assignment_score_audit_log(client, lms_resolver):
    student_assignment1, student_assignment2 = StudentAssignmentFactory.create_batch(2, score=None)
    url = reverse('teaching:api:scores:audit_log', kwargs={
        "student_assignment_id": student_assignment1.pk
    }, subdomain=settings.LMS_SUBDOMAIN)
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, RolePermissionRequiredMixin)
    assert resolver.func.view_class.permission_classes == [EditStudentAssignment]
    assert EditStudentAssignment.name in perm_registry
    # Check unauthorized requests
    response = client.get(url, content_type='application/json')
    assert response.status_code == 401
    client.login(UserFactory())
    response = client.get(url, content_type='application/json')
    assert response.status_code == 403
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(url, content_type='application/json')
    assert response.status_code == 200
    assert 'edges' in response.data
    assert len(response.data['edges']) == 0
    assert 'sources' in response.data
    update_personal_assignment_score(student_assignment=student_assignment1,
                                     changed_by=curator,
                                     score_old=None,
                                     score_new=Decimal(2),
                                     source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT)
    update_personal_assignment_score(student_assignment=student_assignment2,
                                     changed_by=curator,
                                     score_old=None,
                                     score_new=Decimal(3),
                                     source=AssignmentScoreUpdateSource.FORM_GRADEBOOK)
    response = client.get(url, content_type='application/json')
    assert response.status_code == 200
    assert len(response.data['edges']) == 1
    assert response.data['edges'][0]['source'] == AssignmentScoreUpdateSource.FORM_ASSIGNMENT
    assert response.data['edges'][0]['score_new'] == "2.00"
