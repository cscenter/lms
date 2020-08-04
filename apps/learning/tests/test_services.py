import pytest

from core.tests.factories import BranchFactory
from courses.models import StudentGroupTypes
from courses.tests.factories import CourseFactory, AssignmentFactory
from learning.models import StudentGroup, StudentAssignment, \
    AssignmentNotification
from learning.services import StudentGroupService, GroupEnrollmentKeyError, \
    AssignmentService, create_student_profile, StudentProfileError
from learning.settings import Branches, StudentStatuses
from learning.tests.factories import StudentGroupFactory, EnrollmentFactory, \
    AssignmentNotificationFactory
from users.models import StudentTypes, UserGroup
from users.tests.factories import StudentFactory, UserFactory


@pytest.mark.django_db
def test_create_student_profile():
    user = UserFactory()
    branch = BranchFactory()
    # Year of curriculum is required for the REGULAR student type
    with pytest.raises(StudentProfileError):
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
def test_student_group_service_resolve(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    student_group = StudentGroup.objects.get(course=course)
    sg_other = StudentGroupFactory(course=course)
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    assert StudentGroupService.resolve(course, student_spb, settings.SITE_ID) == student_group
    assert StudentGroupService.resolve(course, student_spb, settings.SITE_ID,
                                       enrollment_key='wrong_key') == student_group
    found = StudentGroupService.resolve(
        course, student_spb, settings.SITE_ID,
        enrollment_key=sg_other.enrollment_key)
    assert found == student_group
    assert StudentGroupService.resolve(course, student_nsk, settings.SITE_ID) is None
    course.group_mode = StudentGroupTypes.MANUAL
    assert StudentGroupService.resolve(
        course, student_spb, settings.SITE_ID,
        enrollment_key=sg_other.enrollment_key) == sg_other
    with pytest.raises(GroupEnrollmentKeyError):
        StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key='wrong')


@pytest.mark.django_db
def test_assignment_service_create_student_assignments(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_other = BranchFactory()
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH,
                           branches=[branch_nsk])
    group_spb = StudentGroup.objects.get(course=course, branch=branch_spb)
    group_nsk = StudentGroup.objects.get(course=course, branch=branch_nsk)
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    student_other = StudentFactory(branch=branch_other)
    e_spb = EnrollmentFactory(course=course, student=student_spb)
    e_nsk = EnrollmentFactory(course=course, student=student_nsk)
    e_other = EnrollmentFactory(course=course, student=student_other)
    assignment = AssignmentFactory(course=course)
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 3
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(
        assignment,
        for_groups=[group_spb.pk, group_nsk.pk])
    # Students without student group will be skipped in this case
    assert StudentAssignment.objects.count() == 2
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment, for_groups=[group_nsk.pk])
    ss = StudentAssignment.objects.filter(assignment=assignment)
    assert len(ss) == 1
    assert ss[0].student_id == student_nsk.pk
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment, for_groups=[])
    assert StudentAssignment.objects.count() == 0
    # Check soft deleted enrollments don't taken into account
    e_nsk.is_deleted = True
    e_nsk.save()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 2
    # Inactive status prevents generating student assignment too
    student_spb_profile = student_spb.get_student_profile(settings.SITE_ID)
    student_spb_profile.status = StudentStatuses.ACADEMIC_LEAVE
    student_spb_profile.save()
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 1
    # Now test assignment settings
    student_spb_profile.status = ''
    student_spb_profile.save()
    e_nsk.is_deleted = False
    e_nsk.save()
    assignment.restricted_to.add(group_spb)
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    assert StudentAssignment.objects.get(assignment=assignment).student_id == student_spb.pk
    # Test that only groups from assignment settings get involved
    # if `for_groups` provided
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment, for_groups=[group_spb.pk, group_nsk.pk])
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    assert StudentAssignment.objects.get(assignment=assignment).student_id == student_spb.pk


@pytest.mark.django_db
def test_assignment_service_remove_student_assignments():
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_other = BranchFactory()
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH,
                           branches=[branch_nsk])
    group_spb = StudentGroup.objects.get(course=course, branch=branch_spb)
    group_nsk = StudentGroup.objects.get(course=course, branch=branch_nsk)
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    student_other = StudentFactory(branch=branch_other)
    e_spb = EnrollmentFactory(course=course, student=student_spb)
    e_nsk = EnrollmentFactory(course=course, student=student_nsk)
    e_other = EnrollmentFactory(course=course, student=student_other)
    assignment = AssignmentFactory(course=course)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 3
    AssignmentService.bulk_remove_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 0
    assert StudentAssignment.trash.filter(assignment=assignment).count() == 3
    AssignmentService.bulk_create_student_assignments(assignment)
    AssignmentService.bulk_remove_student_assignments(assignment,
                                                      for_groups=[group_spb.pk])
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 2
    assert StudentAssignment.trash.filter(assignment=assignment).count() == 1
    AssignmentService.bulk_remove_student_assignments(assignment, for_groups=[])
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 2
    # Make sure notifications will be hard deleted
    sa_nsk = StudentAssignment.objects.get(assignment=assignment, student=student_nsk)
    sa_other = StudentAssignment.objects.get(assignment=assignment, student=student_other)
    AssignmentNotification.objects.all().delete()
    AssignmentNotificationFactory(student_assignment=sa_nsk)
    AssignmentNotificationFactory(student_assignment=sa_other)
    assert AssignmentNotification.objects.count() == 2
    AssignmentService.bulk_remove_student_assignments(assignment,
                                                      for_groups=[group_nsk.pk])
    assert AssignmentNotification.objects.count() == 1
    assert AssignmentNotification.objects.filter(student_assignment=sa_other).exists()


@pytest.mark.django_db
def test_assignment_service_sync_student_assignments():
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_other = BranchFactory()
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH,
                           branches=[branch_nsk])
    group_spb = StudentGroup.objects.get(course=course, branch=branch_spb)
    group_nsk = StudentGroup.objects.get(course=course, branch=branch_nsk)
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    student_other = StudentFactory(branch=branch_other)
    e_spb = EnrollmentFactory(course=course, student=student_spb)
    e_nsk = EnrollmentFactory(course=course, student=student_nsk)
    e_other = EnrollmentFactory(course=course, student=student_other)
    assignment = AssignmentFactory(course=course, restricted_to=[group_spb])
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    assert StudentAssignment.objects.get(assignment=assignment).student_id == student_spb.pk
    # [spb] -> [nsk, spb]
    assignment.restricted_to.add(group_nsk)
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 2
    assert not StudentAssignment.objects.filter(assignment=assignment,
                                                student_id=student_other).exists()
    # [nsk, spb] -> all (including manually added students without group)
    assignment.restricted_to.clear()
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 3
    # all -> [nsk]
    assignment.restricted_to.add(group_nsk)
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
