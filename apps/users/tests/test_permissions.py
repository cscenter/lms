import pytest

from users.constants import Roles
from users.models import StudentProfile, UserGroup
from users.tests.factories import StudentFactory


@pytest.mark.django_db
def test_delete_student_profile():
    """Revoke student permissions on deleting student profile"""
    student = StudentFactory(groups=[Roles.INTERVIEWER])
    assert StudentProfile.objects.filter(user=student).exists()
    student_profile = StudentProfile.objects.get(user=student)
    assert UserGroup.objects.filter(user=student).count() == 2
    assert UserGroup.objects.filter(user=student, role=Roles.STUDENT).exists()
    student_group = UserGroup.objects.get(user=student, role=Roles.STUDENT)
    assert student_group.branch == student_profile.branch
    assert student_group.site == student_profile.site
    student_profile.delete()
    assert not UserGroup.objects.filter(user=student, role=Roles.STUDENT).exists()
