from unittest.mock import MagicMock, call

import pytest

from code_reviews.gerrit.services import get_ldap_username, set_reviewers_for_change
from code_reviews.tests.factories import GerritChangeFactory
from learning.models import Enrollment
from learning.tests.factories import StudentGroupAssigneeFactory


class MockedUserGroup:
    def __init__(self, group_name):
        self.created = True
        self.data = {'id': group_name}


@pytest.mark.django_db
def test_set_reviewers_for_change():
    client = MagicMock()

    def return_gerrit_user_group(group_name, **kwargs):
        return MockedUserGroup(group_name=group_name)

    client.create_single_user_group = MagicMock(side_effect=return_gerrit_user_group)
    gerrit_change = GerritChangeFactory()
    student = gerrit_change.student_assignment.student
    course = gerrit_change.student_assignment.assignment.course
    enrollment = Enrollment.objects.get(student=student, course=course)
    # Subscribe student only
    set_reviewers_for_change(client, gerrit_change)
    student_call = call(gerrit_change.change_id,
                        get_ldap_username(student),
                        state='CC', notify='NONE')
    client.set_reviewer.assert_called_once()
    client.set_reviewer.assert_has_calls([student_call])
    client.reset_mock()
    sga1 = StudentGroupAssigneeFactory(student_group=enrollment.student_group)
    # Set teacher as a reviewer and subscribe student to notifications
    set_reviewers_for_change(client, gerrit_change)
    calls = [
        call(gerrit_change.change_id, get_ldap_username(sga1.assignee.teacher),
             state='REVIEWER', notify='NONE'),
        student_call
    ]
    client.set_reviewer.assert_has_calls(calls, any_order=True)
    assignment = gerrit_change.student_assignment.assignment

    client.reset_mock()
    # This one has a higher precedence
    sga2 = StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                       assignment=assignment)

    set_reviewers_for_change(client, gerrit_change)
    calls = [
        student_call,
        call(gerrit_change.change_id,
             get_ldap_username(sga2.assignee.teacher),
             state='REVIEWER', notify='NONE')
    ]
    client.set_reviewer.assert_has_calls(calls, any_order=True)
