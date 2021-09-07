import datetime

import pytest

from django.core.exceptions import ValidationError

from core.tests.factories import BranchFactory, SiteFactory
from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from study_programs.tests.factories import AcademicDisciplineFactory
from users.constants import Roles
from users.models import StudentProfile, StudentTypes, UserGroup
from users.services import (
    StudentStatusTransition, assign_or_revoke_student_role, assign_role,
    create_graduate_profiles, maybe_unassign_student_role, unassign_role
)
from users.tests.factories import CuratorFactory, StudentProfileFactory, UserFactory


@pytest.mark.django_db
def test_create_graduate_profiles():
    site1 = SiteFactory(domain='test.domain')
    site2 = SiteFactory()
    ad = AcademicDisciplineFactory()
    s1 = StudentProfileFactory(status=StudentStatuses.WILL_GRADUATE,
                               branch__site=site1)
    s1.academic_disciplines.add(ad)
    s2 = StudentProfileFactory(status=StudentStatuses.EXPELLED,
                               branch__site=site1)
    s3 = StudentProfileFactory(status=StudentStatuses.WILL_GRADUATE,
                               branch__site=site1)
    s4 = StudentProfileFactory(status=StudentStatuses.WILL_GRADUATE,
                               branch__site=site2)
    assert GraduateProfile.objects.count() == 0
    graduated_on = datetime.date(year=2019, month=11, day=3)
    curator = CuratorFactory()
    create_graduate_profiles(site1, graduated_on, created_by=curator)
    assert GraduateProfile.objects.count() == 2
    assert GraduateProfile.objects.filter(is_active=True).exists()
    graduate_profiles = list(GraduateProfile.objects.order_by('student_profile_id'))
    student_profiles = {g.student_profile_id for g in graduate_profiles}
    assert s1.pk in student_profiles
    assert s3.pk in student_profiles
    g1 = graduate_profiles[0]
    assert g1.student_profile == s1
    assert g1.graduated_on == graduated_on
    assert g1.academic_disciplines.count() == 1
    assert g1.academic_disciplines.all()[0] == ad


@pytest.mark.django_db
def test_assign_role():
    user = UserFactory()
    site1 = SiteFactory(domain='test.domain')
    site2 = SiteFactory()
    assign_role(account=user, role=Roles.TEACHER, site=site1)
    assert user.groups.count() == 1
    assign_role(account=user, role=Roles.TEACHER, site=site1)
    assert user.groups.count() == 1
    assign_role(account=user, role=Roles.TEACHER, site=site2)
    assert user.groups.count() == 2


@pytest.mark.django_db
def test_unassign_role():
    user = UserFactory()
    site1 = SiteFactory(domain='test.domain')
    site2 = SiteFactory()
    assign_role(account=user, role=Roles.TEACHER, site=site1)
    assert user.groups.count() == 1
    user_group = user.groups.get()
    assign_role(account=user, role=Roles.TEACHER, site=site2)
    assert user.groups.count() == 2
    unassign_role(account=user, role=Roles.TEACHER, site=site2)
    assert user.groups.count() == 1
    assert user.groups.get() == user_group
    # This role is not assigned to the student
    unassign_role(account=user, role=Roles.STUDENT, site=site1)
    assert user.groups.count() == 1


def test_resolve_student_status_transition():
    assert StudentStatusTransition.resolve('', '') == StudentStatusTransition.NEUTRAL
    assert StudentStatusTransition.resolve('', StudentStatuses.WILL_GRADUATE) == StudentStatusTransition.NEUTRAL
    assert StudentStatusTransition.resolve('', StudentStatuses.GRADUATE) == StudentStatusTransition.GRADUATION
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE, StudentStatuses.GRADUATE) == StudentStatusTransition.GRADUATION
    assert StudentStatusTransition.resolve('', StudentStatuses.EXPELLED) == StudentStatusTransition.DEACTIVATION
    assert StudentStatusTransition.resolve('', StudentStatuses.ACADEMIC_LEAVE) == StudentStatusTransition.DEACTIVATION
    assert StudentStatusTransition.resolve('', StudentStatuses.ACADEMIC_LEAVE_SECOND) == StudentStatusTransition.DEACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE, StudentStatuses.EXPELLED) == StudentStatusTransition.NEUTRAL
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE_SECOND, StudentStatuses.REINSTATED) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE, StudentStatuses.REINSTATED) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.EXPELLED, StudentStatuses.REINSTATED) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.GRADUATE, StudentStatuses.WILL_GRADUATE) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.GRADUATE, StudentStatuses.EXPELLED) == StudentStatusTransition.DEACTIVATION


@pytest.mark.django_db
def test_maybe_unassign_student_role():
    student_profile = StudentProfileFactory(type=StudentTypes.REGULAR, status=StudentStatuses.REINSTATED)
    user = student_profile.user
    user.groups.all().delete()
    site = student_profile.site
    assign_role(account=user, role=Roles.STUDENT, site=site)
    assert user.groups.count() == 1
    # Not a student role
    with pytest.raises(ValidationError):
        maybe_unassign_student_role(role=Roles.TEACHER, account=user, site=site)
    # No other profiles
    maybe_unassign_student_role(role=Roles.STUDENT, account=user, site=site)
    assert user.groups.count() == 1
    student_profile.status = StudentStatuses.EXPELLED
    student_profile.save()
    maybe_unassign_student_role(role=Roles.STUDENT, account=user, site=site)
    assert user.groups.count() == 0
    # No student profiles of this type
    maybe_unassign_student_role(role=Roles.INVITED, account=user, site=site)


@pytest.mark.django_db
def test_assign_or_revoke_student_role():
    user = UserFactory()
    site1 = SiteFactory(domain='test1.domain')
    site2 = SiteFactory(domain='test2.domain')
    branch = BranchFactory(site=site1)
    student_profile1 = StudentProfileFactory(
        user=user, branch=branch, type=StudentTypes.REGULAR,
        status=StudentStatuses.REINSTATED,
        year_of_admission=2011)
    student_profile2 = StudentProfileFactory(
        user=user, branch=branch, type=StudentTypes.REGULAR,
        status=StudentStatuses.REINSTATED,
        year_of_admission=2013)
    student_profile3 = StudentProfileFactory(
        user=user, branch=BranchFactory(site=site2),
        type=StudentTypes.REGULAR,
        status=StudentStatuses.EXPELLED,
        year_of_admission=2013)
    assert student_profile3.site != student_profile1.site
    UserGroup.objects.all().delete()
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.EXPELLED,
                                  new_status=StudentStatuses.REINSTATED)
    assert user.groups.count() == 1
    assert user.groups.get().role == Roles.STUDENT
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.REINSTATED,
                                  new_status=StudentStatuses.EXPELLED)
    assert user.groups.count() == 1
    StudentProfile.objects.filter(pk=student_profile1.pk).update(status=StudentStatuses.EXPELLED)
    StudentProfile.objects.filter(pk=student_profile2.pk).update(status=StudentStatuses.EXPELLED)
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.REINSTATED,
                                  new_status=StudentStatuses.EXPELLED)
    assert user.groups.count() == 0
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.EXPELLED,
                                  new_status=StudentStatuses.GRADUATE)
    assert user.groups.count() == 1
    assert user.groups.get().role == Roles.GRADUATE
    # Test with a role associated with another site
    assign_or_revoke_student_role(student_profile=student_profile3,
                                  old_status=StudentStatuses.REINSTATED,
                                  new_status=StudentStatuses.EXPELLED)
    assert user.groups.count() == 1
    assert user.groups.get().site_id == site1.pk
    assign_or_revoke_student_role(student_profile=student_profile3,
                                  old_status=StudentStatuses.EXPELLED,
                                  new_status=StudentStatuses.REINSTATED)
    assert user.groups.count() == 2
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.GRADUATE,
                                  new_status=StudentStatuses.EXPELLED)
    assert user.groups.count() == 1
    assert user.groups.get().site_id == site2.pk
    # 1 profile is graduated, 1 is active
    StudentProfile.objects.filter(pk=student_profile1.pk).update(status=StudentStatuses.GRADUATE)
    StudentProfile.objects.filter(pk=student_profile2.pk).update(status=StudentStatuses.REINSTATED)
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.EXPELLED,
                                  new_status=StudentStatuses.GRADUATE)
    assert user.groups.count() == 2
    assign_or_revoke_student_role(student_profile=student_profile1,
                                  old_status=StudentStatuses.EXPELLED,
                                  new_status=StudentStatuses.REINSTATED)
    assert user.groups.count() == 3
    assert UserGroup.objects.filter(site=site1, user=user, role=Roles.STUDENT).exists()
    assert UserGroup.objects.filter(site=site1, user=user, role=Roles.GRADUATE).exists()
    assert UserGroup.objects.filter(site=site2, user=user, role=Roles.STUDENT).exists()
    StudentProfile.objects.filter(pk=student_profile2.pk).update(status=StudentStatuses.GRADUATE)
    assign_or_revoke_student_role(student_profile=student_profile2,
                                  old_status=StudentStatuses.REINSTATED,
                                  new_status=StudentStatuses.GRADUATE)
    assert user.groups.count() == 2
    assert UserGroup.objects.filter(site=site1, user=user, role=Roles.GRADUATE).exists()
    assert UserGroup.objects.filter(site=site2, user=user, role=Roles.STUDENT).exists()

