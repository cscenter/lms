import csv
import datetime
import io
from unittest.mock import patch

import pytest

from django.core.exceptions import ValidationError
from django.forms import model_to_dict
from django.utils import timezone

from core.tests.factories import BranchFactory, SiteFactory
from courses.models import Semester
from courses.tests.factories import CourseFactory, AssignmentFactory
from learning.models import GraduateProfile, Enrollment, StudentAssignment
from learning.settings import StudentStatuses
from learning.tests.factories import InvitationFactory, EnrollmentFactory, AssignmentCommentFactory
from study_programs.tests.factories import (
    AcademicDisciplineFactory, StudyProgramFactory
)
from users.constants import ConsentTypes, Roles
from users.models import StudentProfile, StudentTypes, UserConsent, UserGroup, User, YandexUserData
from users.services import (
    StudentStatusTransition, assign_or_revoke_student_role, assign_role, badge_number_from_csv,
    create_graduate_profiles, create_student_profile, get_student_profile_priority,
    get_student_profiles, give_consent, maybe_unassign_student_role, unassign_role, update_student_status,
    update_student_academic_discipline, merge_users
)
from users.tests.factories import CuratorFactory, StudentProfileFactory, UserFactory, YandexUserDataFactory


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
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE,
                                           StudentStatuses.GRADUATE) == StudentStatusTransition.GRADUATION
    assert StudentStatusTransition.resolve('', StudentStatuses.EXPELLED) == StudentStatusTransition.DEACTIVATION
    assert StudentStatusTransition.resolve('', StudentStatuses.ACADEMIC_LEAVE) == StudentStatusTransition.DEACTIVATION
    assert StudentStatusTransition.resolve('',
                                           StudentStatuses.ACADEMIC_LEAVE_SECOND) == StudentStatusTransition.DEACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE,
                                           StudentStatuses.EXPELLED) == StudentStatusTransition.NEUTRAL
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE_SECOND,
                                           StudentStatuses.REINSTATED) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.ACADEMIC_LEAVE,
                                           StudentStatuses.REINSTATED) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.EXPELLED,
                                           StudentStatuses.REINSTATED) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.GRADUATE,
                                           StudentStatuses.WILL_GRADUATE) == StudentStatusTransition.ACTIVATION
    assert StudentStatusTransition.resolve(StudentStatuses.GRADUATE,
                                           StudentStatuses.EXPELLED) == StudentStatusTransition.DEACTIVATION


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
    previos_semester = current_semester.get_prev()
    invitation = InvitationFactory(semester=current_semester)
    invitation2 = InvitationFactory(semester=previos_semester)
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
    student_profile7 = StudentProfileFactory(type=StudentTypes.INVITED,
                                             invitation=invitation2)
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
    with django_assert_num_queries(4):
        # 1) student profiles 2) empty study programs 3) status history 4) academic discipline history
        student_profiles = get_student_profiles(user=user, site=site1,
                                                fetch_status_history=True)
        for sp in student_profiles:
            assert not sp.studentstatuslog_related.all()
    with django_assert_num_queries(4):
        student_profiles = get_student_profiles(user=user, site=site1)
        for sp in student_profiles:
            assert not sp.studentstatuslog_related.all()
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


@pytest.mark.django_db
def test_update_student_status():
    student_profile = StudentProfileFactory()
    curator = CuratorFactory()
    update_student_status(student_profile,
                          new_status=StudentStatuses.ACADEMIC_LEAVE,
                          editor=curator)

    assert student_profile.status == StudentStatuses.ACADEMIC_LEAVE
    assert Roles.STUDENT not in student_profile.user.roles

    status_logs = student_profile.studentstatuslog_related.all()
    assert len(status_logs) == 1
    status_log = status_logs.first()
    log_dict = model_to_dict(status_log,
                             fields=[field.name for field in status_log._meta.fields if field.name != "id"])
    assert log_dict == {
        "status": StudentStatuses.ACADEMIC_LEAVE,
        "former_status": "",
        "student_profile": student_profile.id,
        "entry_author": curator.id,
        "changed_at": timezone.now().date(),
        "is_processed": False,
        "processed_at": None
    }

    tomorrow = timezone.now().date() + datetime.timedelta(days=1)
    update_student_status(student_profile,
                          new_status=StudentStatuses.REINSTATED,
                          editor=curator,
                          changed_at=tomorrow)
    student_profile.refresh_from_db()
    assert student_profile.status == StudentStatuses.REINSTATED
    assert Roles.STUDENT in student_profile.user.roles

    status_logs = student_profile.studentstatuslog_related.all()
    assert len(status_logs) == 2
    assert status_logs.last() == status_log
    status_log = status_logs.first()
    log_dict = model_to_dict(status_log,
                             fields=[field.name for field in status_log._meta.fields if field.name != "id"])
    assert log_dict == {
        "status": StudentStatuses.REINSTATED,
        "former_status": StudentStatuses.ACADEMIC_LEAVE,
        "student_profile": student_profile.id,
        "entry_author": curator.id,
        "changed_at": tomorrow,
        "is_processed": False,
        "processed_at": None
    }
    with pytest.raises(ValidationError):
        update_student_status(student_profile,
                              new_status="unknown_status",
                              editor=curator)

    student_profile.type = StudentTypes.INVITED
    with pytest.raises(ValidationError):
        update_student_status(student_profile,
                              new_status=StudentStatuses.GRADUATE,
                              editor=curator)


@pytest.mark.django_db
def test_update_student_academic_discipline():
    student_profile = StudentProfileFactory()
    curator = CuratorFactory()
    academic_discipline = AcademicDisciplineFactory()
    update_student_academic_discipline(student_profile,
                                       new_academic_discipline=academic_discipline,
                                       editor=curator)

    assert student_profile.academic_discipline == academic_discipline

    discipline_logs = student_profile.studentacademicdisciplinelog_related.all()
    assert len(discipline_logs) == 1
    discipline_log = discipline_logs.first()
    log_dict = model_to_dict(discipline_log,
                             fields=[field.name for field in discipline_log._meta.fields if field.name != "id"])
    assert log_dict == {
        "academic_discipline": academic_discipline.id,
        "former_academic_discipline": None,
        "student_profile": student_profile.id,
        "entry_author": curator.id,
        "changed_at": timezone.now().date(),
        "is_processed": False,
        "processed_at": None
    }

    tomorrow = timezone.now().date() + datetime.timedelta(days=1)
    other_academic_discipline = AcademicDisciplineFactory()
    update_student_academic_discipline(student_profile,
                                       new_academic_discipline=other_academic_discipline,
                                       editor=curator,
                                       changed_at=tomorrow)
    student_profile.refresh_from_db()
    assert student_profile.academic_discipline == other_academic_discipline

    discipline_logs = student_profile.studentacademicdisciplinelog_related.all()
    assert len(discipline_logs) == 2
    assert discipline_logs.last() == discipline_log
    discipline_log = discipline_logs.first()
    log_dict = model_to_dict(discipline_log,
                             fields=[field.name for field in discipline_log._meta.fields if field.name != "id"])
    assert log_dict == {
        "academic_discipline": other_academic_discipline.id,
        "former_academic_discipline": academic_discipline.id,
        "student_profile": student_profile.id,
        "entry_author": curator.id,
        "changed_at": tomorrow,
        "is_processed": False,
        "processed_at": None
    }


@pytest.mark.django_db
@pytest.mark.parametrize("minor_user", [111, "str", None])
def test_merge_users_failed(minor_user):
    major_user = UserFactory()
    with pytest.raises(TypeError):
        merge_users(major=major_user, minor=minor_user)
    with pytest.raises(ValueError):
        merge_users(major=major_user, minor=major_user)


@pytest.mark.django_db
def test_merge_users_completed():
    '''
    _merge means this object will merge with major object using recursive call of merge_objects
    _transfer means this object will be automatically rearranged to parent major object using setattr
    _autotransfer means this object will be automatically rearranged to major by parent object transfer
    '''
    common_branch = BranchFactory()
    major_user = UserFactory(first_name="")
    minor_user = UserFactory(branch=common_branch)
    minor_yandex_data = YandexUserDataFactory(user=minor_user)
    common_course = CourseFactory()
    major_profile = StudentProfileFactory(user=major_user, branch=common_branch)
    minor_profile_merge = StudentProfileFactory(user=minor_user, branch=common_branch,
                                                year_of_curriculum=2024, is_official_student=True)
    minor_profile_transfer = StudentProfileFactory(user=minor_user)
    major_enrollment = EnrollmentFactory(student=major_user,
                                         student_profile=major_profile,
                                         course=common_course)
    minor_enrollment_merge = EnrollmentFactory(student=minor_user,
                                         student_profile=minor_profile_merge,
                                         course=common_course,
                                         reason_entry="significant_reason")
    minor_enrollment_transfer = EnrollmentFactory(student=minor_user,
                                                student_profile=minor_profile_merge)
    minor_enrollment_autotransfer = EnrollmentFactory(student=minor_user,
                                                  student_profile=minor_profile_transfer)
    common_assignment = AssignmentFactory(course=common_course)
    major_assignment = StudentAssignment.objects.get(assignment=common_assignment, student=major_user)
    minor_assignment_merge = StudentAssignment.objects.get(assignment=common_assignment, student=minor_user)
    minor_assignment_merge.score = 5
    minor_assignment_merge.save()
    uncommon_assignment = AssignmentFactory(course=minor_enrollment_autotransfer.course)
    minor_assignment_autotransfer = StudentAssignment.objects.get(assignment=uncommon_assignment, student=minor_user)
    major_comment = AssignmentCommentFactory(student_assignment=major_assignment, author=major_user)
    minor_comment_autotransfer = AssignmentCommentFactory(student_assignment=minor_assignment_merge, author=minor_user)

    major_user = merge_users(major=major_user, minor=minor_user)

    assert set(major_user.student_profiles.all()) == {major_profile, minor_profile_transfer}
    assert set(minor_profile_transfer.enrollment_set.all()) == {minor_enrollment_autotransfer}
    assert set(major_profile.enrollment_set.all()) == {major_enrollment, minor_enrollment_transfer}
    assert set(major_user.studentassignment_set.all()) == {major_assignment, minor_assignment_autotransfer}
    assert set(major_user.assignmentcomment_set.all()) == {major_comment, minor_comment_autotransfer}
    assert set(major_assignment.assignmentcomment_set.all()) == {major_comment, minor_comment_autotransfer}
    assert major_user.first_name == minor_user.first_name
    assert major_user.branch == common_branch

    assert major_profile.year_of_curriculum is None
    assert not major_profile.is_official_student
    major_profile.refresh_from_db()
    assert major_profile.year_of_curriculum == 2024
    assert not major_profile.is_official_student

    assert major_enrollment.reason_entry == ""
    major_enrollment.refresh_from_db()
    assert major_enrollment.reason_entry == "significant_reason"

    assert major_assignment.score is None
    major_assignment.refresh_from_db()
    assert major_assignment.score == 5

    assert not User.objects.filter(id=minor_user.id).exists()
    assert not StudentProfile.objects.filter(id=minor_profile_merge.id).exists()
    assert not Enrollment.objects.filter(id=minor_enrollment_merge.id).exists()
    assert not StudentAssignment.objects.filter(id=minor_assignment_merge.id).exists()
    assert not YandexUserData.objects.filter(user=major_user).exists()
    assert not YandexUserData.objects.filter(id=minor_yandex_data.id).exists()


@pytest.mark.django_db
def test_merge_users_failed():
    user1 = UserFactory()
    user2 = UserFactory()
    csv_file = io.StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Не Почта', 'Не Номер пропуска'])
    csv_writer.writerow([user1.email, 'test badge 1'])
    csv_file.seek(0)
    with pytest.raises(ValidationError):
        badge_number_from_csv(csv_file)
    csv_file = io.StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Почта', 'Номер пропуска'])
    csv_writer.writerow([user1.email, 'test badge 1'])
    csv_writer.writerow(['wrong email', 'test badge 2'])
    csv_file.seek(0)
    with pytest.raises(ValueError):
        badge_number_from_csv(csv_file)
    csv_file = io.StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Почта', 'Номер пропуска'])
    csv_writer.writerow([user1.email, 'test badge 1'])
    csv_writer.writerow([user2.email, 'test badge 2'])
    csv_file.seek(0)
    assert badge_number_from_csv(csv_file) == 2

@pytest.mark.django_db
def test_give_consent():
    user = UserFactory()
    for consent_type in ConsentTypes.regular_student_consents:
        give_consent(user, consent_type)
    time = timezone.now()
    user_consents = UserConsent.objects.filter(user=user)
    assert set(user_consents.values_list("type", flat=True)) == ConsentTypes.regular_student_consents
    assert all(time - created <= datetime.timedelta(seconds=5) for created in user_consents.values_list("created", flat=True))
    with patch('django.utils.timezone.now') as mocked_now:
        mocked_now.return_value = time + datetime.timedelta(seconds=10)
        
        for consent_type in ConsentTypes.invited_student_consents:
            give_consent(user, consent_type)
        time = timezone.now()
        user_consents = UserConsent.objects.filter(user=user)
        assert set(user_consents.values_list("type", flat=True)) == ConsentTypes.regular_student_consents
        new_user_consents = user_consents.filter(type__in=ConsentTypes.invited_student_consents)
        old_user_consents = user_consents.exclude(type__in=ConsentTypes.invited_student_consents)
        assert all(time - created <= datetime.timedelta(seconds=5) for created in new_user_consents.values_list("created", flat=True))
        assert all(time - created > datetime.timedelta(seconds=5) for created in old_user_consents.values_list("created", flat=True))
