import datetime

import pytest
from django.conf import settings

from django.core.exceptions import ValidationError

from core.tests.factories import BranchFactory, SiteFactory
from core.timezone import now_local
from courses.models import Semester
from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from learning.tests.factories import InvitationFactory, EnrollmentPeriodFactory
from study_programs.tests.factories import (
    AcademicDisciplineFactory, StudyProgramFactory
)
from users.constants import Roles
from users.models import StudentProfile, StudentTypes, UserGroup
from users.services import (
    StudentStatusTransition, assign_or_revoke_student_role, assign_role,
    create_graduate_profiles, create_student_profile, get_student_profile_priority,
    get_student_profiles, maybe_unassign_student_role, unassign_role
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


@pytest.mark.django_db
def test_get_student_profile_priority():
    student_profile1 = StudentProfileFactory(type=StudentTypes.REGULAR,
                                             status=StudentStatuses.REINSTATED)
    current_semester = Semester.get_current()
    invitation = InvitationFactory(semester=current_semester)
    today = now_local(student_profile1.branch.get_timezone()).date()
    EnrollmentPeriodFactory(semester=current_semester,
                                               site_id=settings.SITE_ID,
                                               starts_on=today,
                                               ends_on=today)
    student_profile2 = StudentProfileFactory(type=StudentTypes.INVITED,
                                             status=StudentStatuses.REINSTATED,
                                             invitation=invitation)
    assert get_student_profile_priority(student_profile1) < get_student_profile_priority(student_profile2)
    student_profile3 = StudentProfileFactory(type=StudentTypes.REGULAR,
                                             status=StudentStatuses.EXPELLED)
    assert get_student_profile_priority(student_profile1) < get_student_profile_priority(student_profile3)
    student_profile4 = StudentProfileFactory(type=StudentTypes.REGULAR,
                                             status=StudentStatuses.GRADUATE)
    assert get_student_profile_priority(student_profile1) < get_student_profile_priority(student_profile4)
    student_profile5 = StudentProfileFactory(type=StudentTypes.REGULAR,
                                             status=StudentStatuses.EXPELLED)
    assert get_student_profile_priority(student_profile2) < get_student_profile_priority(student_profile5)
    student_profile6 = StudentProfileFactory(type=StudentTypes.VOLUNTEER,
                                             status=StudentStatuses.EXPELLED)
    assert get_student_profile_priority(student_profile5) == get_student_profile_priority(student_profile6)
    student_profile7 = StudentProfileFactory(type=StudentTypes.INVITED)
    assert get_student_profile_priority(student_profile3) < get_student_profile_priority(student_profile7)
    assert get_student_profile_priority(student_profile4) < get_student_profile_priority(student_profile7)
    assert get_student_profile_priority(student_profile5) < get_student_profile_priority(student_profile7)


@pytest.mark.django_db
def test_create_student_profile():
    user = UserFactory()
    branch = BranchFactory()
    # Year of curriculum is required for the REGULAR student type
    with pytest.raises(ValidationError):
        create_student_profile(user=user, branch=branch,
                               profile_type=StudentTypes.REGULAR,
                               year_of_admission=2020)
    student_profile = create_student_profile(user=user, branch=branch,
                                             profile_type=StudentTypes.REGULAR,
                                             year_of_admission=2020,
                                             year_of_curriculum=2019)
    assert student_profile.user == user
    assert student_profile.site_id == branch.site_id
    assert student_profile.type == StudentTypes.REGULAR
    assert student_profile.year_of_admission == 2020
    assert student_profile.year_of_curriculum == 2019
    assert UserGroup.objects.filter(user=user)
    assert UserGroup.objects.filter(user=user).count() == 1
    permission_group = UserGroup.objects.get(user=user)
    assert permission_group.role == StudentTypes.to_permission_role(StudentTypes.REGULAR)
    profile = create_student_profile(user=user, branch=branch,
                                     profile_type=StudentTypes.INVITED,
                                     year_of_admission=2020)
    assert profile.year_of_curriculum is None


@pytest.mark.django_db
def test_delete_student_profile():
    """
    Revoke student permissions on site only if no other student profiles of
    the same type are exist after removing profile.
    """
    user = UserFactory()
    branch = BranchFactory()
    student_profile = create_student_profile(user=user, branch=branch,
                                             profile_type=StudentTypes.INVITED,
                                             year_of_admission=2020)
    student_profile1 = create_student_profile(user=user, branch=branch,
                                              profile_type=StudentTypes.REGULAR,
                                              year_of_admission=2020,
                                              year_of_curriculum=2019)
    student_profile2 = create_student_profile(user=user, branch=branch,
                                              profile_type=StudentTypes.REGULAR,
                                              year_of_admission=2021,
                                              year_of_curriculum=2019)
    assert UserGroup.objects.filter(user=user).count() == 2
    student_profile1.delete()
    assert UserGroup.objects.filter(user=user).count() == 2
    student_profile2.delete()
    assert UserGroup.objects.filter(user=user).count() == 1
    permission_group = UserGroup.objects.get(user=user)
    assert permission_group.role == StudentTypes.to_permission_role(StudentTypes.INVITED)


@pytest.mark.django_db
def test_get_student_profiles(django_assert_num_queries):
    user = UserFactory()
    site1 = SiteFactory(domain='test1.ru')
    site2 = SiteFactory(domain='test2.ru')
    branch1 = BranchFactory(site=site1)
    student_profile1 = create_student_profile(user=user, branch=branch1,
                                              profile_type=StudentTypes.INVITED,
                                              year_of_admission=2020)
    student_profile2 = create_student_profile(user=user, branch=branch1,
                                              profile_type=StudentTypes.REGULAR,
                                              year_of_admission=2020,
                                              year_of_curriculum=2020)
    student_profiles = get_student_profiles(user=user, site=site1)
    assert len(student_profiles) == 2
    assert student_profile2.priority < student_profile1.priority
    assert student_profile1 == student_profiles[1]
    assert student_profile2 == student_profiles[0]  # higher priority
    with django_assert_num_queries(3):
        # 1) student profiles 2) empty study programs 3) status history
        student_profiles = get_student_profiles(user=user, site=site1,
                                                fetch_status_history=True)
        for sp in student_profiles:
            assert not sp.status_history.all()
    with django_assert_num_queries(4):
        student_profiles = get_student_profiles(user=user, site=site1)
        for sp in student_profiles:
            assert not sp.status_history.all()
    with django_assert_num_queries(1):
        assert get_student_profiles(user=user, site=site2) == []
    with django_assert_num_queries(1):
        get_student_profiles(user=user, site=site2, fetch_status_history=True)


@pytest.mark.django_db
def test_get_student_profiles_prefetch_syllabus(django_assert_num_queries):
    user = UserFactory()
    site1 = SiteFactory(domain='test1.ru')
    site2 = SiteFactory(domain='test2.ru')
    branch1 = BranchFactory(site=site1)
    branch2 = BranchFactory(site=site2)
    student_profile1 = create_student_profile(user=user, branch=branch1,
                                              profile_type=StudentTypes.INVITED,
                                              year_of_admission=2019,
                                              year_of_curriculum=2019)
    student_profile2 = create_student_profile(user=user, branch=branch1,
                                              profile_type=StudentTypes.REGULAR,
                                              year_of_admission=2020,
                                              year_of_curriculum=2020)
    student_profile3 = create_student_profile(user=user, branch=branch1,
                                              profile_type=StudentTypes.REGULAR,
                                              year_of_admission=2019,
                                              year_of_curriculum=2019)
    study_program_2020_1 = StudyProgramFactory(year=2020, branch=branch1)
    study_program_2020_2 = StudyProgramFactory(year=2020, branch=branch1)
    study_program_2019 = StudyProgramFactory(year=2019, branch=branch1)
    study_program_other = StudyProgramFactory(year=2020, branch=branch2)
    student_profiles = get_student_profiles(user=user, site=site1)
    assert len(student_profiles) == 3
    assert student_profile2 == student_profiles[0]
    assert 'syllabus' in student_profiles[0].__dict__
    assert student_profiles[0].syllabus == student_profile2.syllabus
    syllabus = student_profiles[0].syllabus
    assert len(syllabus) == 2
    assert study_program_2020_1 in syllabus
    assert study_program_2020_2 in syllabus
    assert 'syllabus' in student_profiles[1].__dict__
    assert student_profiles[1].syllabus == student_profile3.syllabus
    syllabus = student_profiles[1].syllabus
    assert len(syllabus) == 1
    assert study_program_2019 in syllabus
    assert student_profile1 == student_profiles[2]
    assert 'syllabus' in student_profiles[1].__dict__
    assert student_profiles[2].syllabus == student_profile1.syllabus
    assert student_profiles[2].syllabus is None
