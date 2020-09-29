from unittest.mock import MagicMock

import pytest

from code_reviews.gerrit import set_reviewers_for_change
from code_reviews.ldap import get_ldap_username
from code_reviews.tests.factories import GerritChangeFactory
from learning.tests.factories import StudentGroupAssigneeFactory, \
    EnrollmentFactory


@pytest.mark.django_db
def test_set_reviewers_for_change():
    client = MagicMock()
    gerrit_change = GerritChangeFactory()
    student = gerrit_change.student_assignment.student
    course = gerrit_change.student_assignment.assignment.course
    enrollment = EnrollmentFactory(student=student, course=course)
    set_reviewers_for_change(client, gerrit_change)
    client.set_reviewer.assert_not_called()
    sga1 = StudentGroupAssigneeFactory(student_group=enrollment.student_group)
    set_reviewers_for_change(client, gerrit_change)
    client.set_reviewer.assert_called_with(gerrit_change.change_id,
                                           get_ldap_username(sga1.assignee))
    assignment = gerrit_change.student_assignment.assignment
    sga2 = StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                       assignment=assignment)
    client = MagicMock()
    set_reviewers_for_change(client, gerrit_change)
    client.set_reviewer.assert_called_once_with(
        gerrit_change.change_id, get_ldap_username(sga2.assignee))
