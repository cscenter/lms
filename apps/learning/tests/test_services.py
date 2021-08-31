from datetime import timedelta

import pytest

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.tests.factories import BranchFactory, SiteFactory
from core.tests.settings import ANOTHER_DOMAIN, ANOTHER_DOMAIN_ID, TEST_DOMAIN
from core.timezone import get_now_utc
from courses.models import (
    CourseBranch, CourseGroupModes, CourseTeacher, StudentGroupTypes
)
from courses.services import CourseService
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.models import (
    AssignmentNotification, Enrollment, StudentAssignment, StudentGroup,
    StudentGroupAssignee
)
from learning.services import (
    AssignmentService, EnrollmentService, GroupEnrollmentKeyError, StudentGroupError,
    StudentGroupService, create_notifications_about_new_submission
)
from learning.settings import Branches, StudentStatuses
from learning.tests.factories import (
    AssignmentCommentFactory, AssignmentNotificationFactory, EnrollmentFactory,
    StudentAssignmentFactory, StudentGroupAssigneeFactory, StudentGroupFactory
)
from users.models import StudentTypes, UserGroup
from users.services import StudentProfileError, create_student_profile
from users.tests.factories import StudentFactory, StudentProfileFactory, UserFactory


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
def test_student_group_service_create_no_groups_mode(settings):
    course = CourseFactory(group_mode=CourseGroupModes.NO_GROUPS)
    with pytest.raises(StudentGroupError) as e:
        StudentGroupService.create(course, branch=course.main_branch)


@pytest.mark.django_db
def test_student_group_service_create_with_branch_mode(settings):
    branch1, branch2 = BranchFactory.create_batch(2)
    course = CourseFactory(main_branch=branch1,
                           group_mode=CourseGroupModes.BRANCH)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course, branch=branch2)
    assert e.value.code == 'malformed'
    student_group1 = StudentGroupService.create(course, branch=branch1)
    assert list(StudentGroup.objects.all()) == [student_group1]
    StudentGroupService.create(course, branch=branch1)  # repeat
    assert StudentGroup.objects.count() == 1


@pytest.mark.django_db
def test_student_group_service_create_manual_group(settings):
    course1, course2 = CourseFactory.create_batch(2, group_mode=CourseGroupModes.MANUAL)
    # Empty group name
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course1)
    assert e.value.code == 'required'
    student_group = StudentGroupService.create(course1, name='test')
    assert list(StudentGroup.objects.all()) == [student_group]
    # Non unique student group name for the course
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course1, name='test')
    StudentGroupService.create(course2, name='test')


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
    student_group = StudentGroupService.resolve(course, student_nsk, settings.SITE_ID)
    assert student_group.type == StudentGroupTypes.SYSTEM
    course.group_mode = CourseGroupModes.MANUAL
    assert StudentGroupService.resolve(
        course, student_spb, settings.SITE_ID,
        enrollment_key=sg_other.enrollment_key) == sg_other
    with pytest.raises(GroupEnrollmentKeyError):
        StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key='wrong')
    student_group = StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key=None)
    assert student_group.type == StudentGroupTypes.SYSTEM
    course.group_mode = 'unknown'
    with pytest.raises(GroupEnrollmentKeyError):
        StudentGroupService.resolve(course, student_spb, settings.SITE_ID, enrollment_key='wrong')


@pytest.mark.django_db
def test_student_group_service_get_choices(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    groups = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert len(choices) == 1
    assert choices[0] == (str(groups[0].pk), groups[0].name)
    branch_nsk = BranchFactory(code=Branches.NSK,
                               site=SiteFactory(domain=ANOTHER_DOMAIN))
    assert branch_nsk.site_id == ANOTHER_DOMAIN_ID
    CourseBranch(course=course, branch=branch_nsk).save()
    assert StudentGroup.objects.filter(course=course).count() == 2
    sg1, sg2 = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert choices[0] == (str(sg1.pk), f"{sg1.name} [{TEST_DOMAIN}]")
    assert choices[1] == (str(sg2.pk), f"{sg2.name} [{ANOTHER_DOMAIN}]")


@pytest.mark.django_db
def test_student_group_service_get_student_profiles():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    enrollments = EnrollmentFactory.create_batch(3, course=course, student_group=student_group1)
    enrollment1, enrollment2, enrollment3 = enrollments
    student_profiles = StudentGroupService.get_student_profiles(student_group2)
    assert len(student_profiles) == 0
    EnrollmentFactory(course=course, student_group=student_group2)
    student_profiles = StudentGroupService.get_student_profiles(student_group1)
    assert len(student_profiles) == 3
    EnrollmentService.leave(enrollment1, reason_leave='cause')
    student_profiles = StudentGroupService.get_student_profiles(student_group1)
    assert len(student_profiles) == 2


@pytest.mark.django_db
def test_student_group_service_get_groups_available_for_student_transfer():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2, student_group3 = StudentGroupFactory.create_batch(3, course=course)
    student_group4 = StudentGroupFactory(course__group_mode=StudentGroupTypes.MANUAL)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 2
    assert student_group2 in student_groups
    assert student_group3 in student_groups
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group4)
    assert len(student_groups) == 0
    assignment1, assignment2 = AssignmentFactory.create_batch(2, course=course)
    assignment1.restricted_to.add(student_group2, student_group3)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 0
    assignment1.restricted_to.add(student_group1)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 2
    assert student_group2 in student_groups
    assert student_group3 in student_groups
    assignment2.restricted_to.add(student_group2)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group3 in student_groups
    assignment2.restricted_to.add(student_group1)
    student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group2 in student_groups


@pytest.mark.django_db
def test_student_group_add_assignees(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory()
    course_teacher1, course_teacher2 = CourseTeacherFactory.create_batch(2, course=course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assigned = StudentGroupAssignee.objects.get()
    assert assigned.assignee_id == course_teacher1.pk
    # Student group does not match course of the course teacher
    with pytest.raises(ValidationError):
        StudentGroupService.add_assignees(student_group2, teachers=[course_teacher1])
    # Can't add the same course teacher twice
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assignment = AssignmentFactory(course=course)
    # Customize list of responsible teachers for the assignment
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)
    assert StudentGroupAssignee.objects.count() == 2
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)


@pytest.mark.django_db
def test_student_group_update_assignees(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    course_teacher1, course_teacher2, course_teacher3 = CourseTeacherFactory.create_batch(3, course=course)
    student_group2 = StudentGroupFactory()
    course_teacher2_1 = CourseTeacherFactory(course=student_group2.course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assigned = StudentGroupAssignee.objects.get()
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assert StudentGroupAssignee.objects.get() == assigned
    StudentGroupService.update_assignees(student_group2, teachers=[course_teacher2_1])
    assert StudentGroupAssignee.objects.count() == 2
    assert assigned in StudentGroupAssignee.objects.all()
    # Add the second course teacher and try to update list of responsible
    # teachers again
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher2])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 1
    assert StudentGroupAssignee.objects.count() == 2
    # Assign responsible teachers for the assignment
    assignment = AssignmentFactory(course=course)
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher2], assignment=assignment)
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    assert StudentGroupService.get_assignees(student_group1) == [course_teacher1]
    assert StudentGroupService.get_assignees(student_group1, assignment=assignment) == [course_teacher2]
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)
    assert StudentGroupService.get_assignees(student_group1, assignment=assignment) == [course_teacher1]
    # Reset list of teachers
    StudentGroupService.update_assignees(student_group1, teachers=[], assignment=assignment)
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 1
    assert StudentGroupAssignee.objects.filter(student_group=student_group1, assignment=assignment).count() == 0
    assert assigned in StudentGroupAssignee.objects.filter(student_group=student_group1).all()
    # Add and delete at the same time
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher3])
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1, course_teacher2])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    assigned_teachers = [sga.assignee for sga in StudentGroupAssignee.objects.filter(student_group=student_group1)]
    assert course_teacher1 in assigned_teachers
    assert course_teacher2 in assigned_teachers
    assert StudentGroupAssignee.objects.filter(student_group=student_group2).count() == 1


@pytest.mark.django_db
def test_student_group_get_assignees():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    assignment1 = AssignmentFactory(course=course)
    assignment2 = AssignmentFactory(course=course)
    assert StudentGroup.objects.filter(course=course).count() == 0
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory(course=course)
    sga1 = StudentGroupAssigneeFactory(student_group=student_group1)
    sga2 = StudentGroupAssigneeFactory(student_group=student_group1)
    sga3 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment1)
    sga4 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment1)
    sga5 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment2)
    assert StudentGroupService.get_assignees(student_group2) == []
    assignees = StudentGroupService.get_assignees(student_group1)
    assert len(assignees) == 2
    assert sga1.assignee in assignees
    assert sga2.assignee in assignees
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment1)
    assert len(assignees) == 2
    assert sga3.assignee in assignees
    assert sga4.assignee in assignees
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga5.assignee == assignees[0]
    sga6 = StudentGroupAssigneeFactory(student_group=student_group2,
                                       assignment=assignment2)
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga5.assignee == assignees[0]
    assignees = StudentGroupService.get_assignees(student_group2,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga6.assignee == assignees[0]


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
    student_profile_spb = StudentProfileFactory(branch=branch_spb)
    student_profile_nsk = StudentProfileFactory(branch=branch_nsk)
    student_profile_other = StudentProfileFactory(branch=branch_other)
    e_spb = EnrollmentFactory(course=course,
                              student_profile=student_profile_spb,
                              student=student_profile_spb.user)
    e_nsk = EnrollmentFactory(course=course,
                              student_profile=student_profile_nsk,
                              student=student_profile_nsk.user)
    e_other = EnrollmentFactory(course=course,
                                student_profile=student_profile_other,
                                student=student_profile_other.user)
    assert Enrollment.active.count() == 3
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
    assert ss[0].student_id == student_profile_nsk.user_id
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment, for_groups=[])
    assert StudentAssignment.objects.count() == 0
    # Check soft deleted enrollments don't taken into account
    e_nsk.is_deleted = True
    e_nsk.save()
    assert Enrollment.active.count() == 2
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 2
    # Inactive status prevents generating student assignment too
    student_profile_spb.status = StudentStatuses.ACADEMIC_LEAVE
    student_profile_spb.save()
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 1
    # Now test assignment settings
    student_profile_spb.status = ''
    student_profile_spb.save()
    e_nsk.is_deleted = False
    e_nsk.save()
    assignment.restricted_to.add(group_spb)
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    assert StudentAssignment.objects.get(assignment=assignment).student_id == student_profile_spb.user_id
    # Test that only groups from assignment settings get involved
    # if `for_groups` provided
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment, for_groups=[group_spb.pk, group_nsk.pk])
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    assert StudentAssignment.objects.get(assignment=assignment).student_id == student_profile_spb.user_id


@pytest.mark.parametrize("inactive_status", [StudentStatuses.ACADEMIC_LEAVE,
                                             StudentStatuses.ACADEMIC_LEAVE_SECOND,
                                             StudentStatuses.EXPELLED])
@pytest.mark.django_db
def test_assignment_service_create_student_assignments_inactive_status(inactive_status, settings):
    """
    Inactive student profile status prevents from generating assignment
    record for student.
    """
    branch = BranchFactory()
    course = CourseFactory(main_branch=branch,
                           group_mode=StudentGroupTypes.BRANCH,
                           branches=[branch])
    assignment = AssignmentFactory(course=course)
    student_profile = StudentProfileFactory(branch=branch)
    EnrollmentFactory(course=course,
                      student_profile=student_profile,
                      student=student_profile.user)
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 1
    # Set inactive status
    StudentAssignment.objects.all().delete()
    student_profile.status = inactive_status
    student_profile.save()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.count() == 0


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
    student_profile_spb = StudentProfileFactory(branch=branch_spb)
    student_profile_nsk = StudentProfileFactory(branch=branch_nsk)
    student_profile_other = StudentProfileFactory(branch=branch_other)
    e_spb = EnrollmentFactory(course=course,
                              student_profile=student_profile_spb,
                              student=student_profile_spb.user)
    e_nsk = EnrollmentFactory(course=course,
                              student_profile=student_profile_nsk,
                              student=student_profile_nsk.user)
    e_other = EnrollmentFactory(course=course,
                                student_profile=student_profile_other,
                                student=student_profile_other.user)
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
    sa_nsk = StudentAssignment.objects.get(assignment=assignment, student=student_profile_nsk.user)
    sa_other = StudentAssignment.objects.get(assignment=assignment, student=student_profile_other.user)
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
    student_profile_spb = StudentProfileFactory(branch=branch_spb)
    student_profile_nsk = StudentProfileFactory(branch=branch_nsk)
    student_profile_other = StudentProfileFactory(branch=branch_other)
    e_spb = EnrollmentFactory(course=course, student=student_profile_spb.user,
                              student_profile=student_profile_spb)
    e_nsk = EnrollmentFactory(course=course, student=student_profile_nsk.user,
                              student_profile=student_profile_nsk)
    e_other = EnrollmentFactory(course=course, student=student_profile_other.user,
                                student_profile=student_profile_other)
    assignment = AssignmentFactory(course=course, restricted_to=[group_spb])
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    assert StudentAssignment.objects.get(assignment=assignment).student_id == student_profile_spb.user_id
    # [spb] -> [nsk, spb]
    assignment.restricted_to.add(group_nsk)
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 2
    assert not StudentAssignment.objects.filter(assignment=assignment,
                                                student_id=student_profile_other.user_id).exists()
    # [nsk, spb] -> all (including manually added students without group)
    assignment.restricted_to.clear()
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 3
    # all -> [nsk]
    assignment.restricted_to.add(group_nsk)
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 1
    # [nsk] -> [nsk, spb]
    assignment.restricted_to.add(group_spb)
    AssignmentService.sync_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 2


@pytest.mark.django_db
def test_mean_execution_time():
    assignment = AssignmentFactory()
    assert AssignmentService.get_mean_execution_time(assignment) is None
    sa1 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(hours=2, minutes=4))
    assert AssignmentService.get_mean_execution_time(assignment) == timedelta(hours=2, minutes=4)
    sa2 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(hours=4, minutes=12))
    assert AssignmentService.get_mean_execution_time(assignment) == timedelta(hours=3, minutes=8)
    sa3 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(minutes=56))
    assert AssignmentService.get_mean_execution_time(assignment) == timedelta(hours=2, minutes=24)


@pytest.mark.django_db
def test_median_execution_time():
    assignment = AssignmentFactory()
    assert AssignmentService.get_median_execution_time(assignment) is None
    sa1 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(hours=2, minutes=4))
    assert AssignmentService.get_median_execution_time(assignment) == timedelta(hours=2, minutes=4)
    sa2 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(hours=4, minutes=12))
    assert AssignmentService.get_median_execution_time(assignment) == timedelta(hours=3, minutes=8)
    sa3 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(minutes=56))
    assert AssignmentService.get_median_execution_time(assignment) == timedelta(hours=2, minutes=4)
    sa4 = StudentAssignmentFactory(assignment=assignment,
                                   execution_time=timedelta(minutes=4))
    assert AssignmentService.get_median_execution_time(assignment) == timedelta(hours=1, minutes=30)


@pytest.mark.django_db
def test_create_notifications_about_new_submission():
    student_assignment = StudentAssignmentFactory()
    student = student_assignment.student
    course = student_assignment.assignment.course
    comment = AssignmentCommentFactory(author=student,
                                       student_assignment=student_assignment)
    AssignmentNotification.objects.all().delete()
    create_notifications_about_new_submission(comment)
    assert AssignmentNotification.objects.count() == 0
    # Add course teacher without reviewer role
    ct1 = CourseTeacherFactory(course=course)
    create_notifications_about_new_submission(comment)
    assert AssignmentNotification.objects.count() == 0
    # Add course teachers with a reviewer role
    ct2 = CourseTeacherFactory(course=course,
                               roles=CourseTeacher.roles.reviewer,
                               notify_by_default=True)
    ct3 = CourseTeacherFactory(course=course,
                               roles=CourseTeacher.roles.reviewer,
                               notify_by_default=True)
    create_notifications_about_new_submission(comment)
    assert AssignmentNotification.objects.count() == 2
    # Assign student assignment to teacher
    student_assignment.assignee = ct2
    student_assignment.save()
    AssignmentNotification.objects.all().delete()
    create_notifications_about_new_submission(comment)
    notifications = (AssignmentNotification.objects
                     .filter(student_assignment=student_assignment))
    assert notifications.count() == 1
    assert notifications[0].user == ct2.teacher
    student_assignment.assignee = None
    student_assignment.save()
    # Add student group assignees
    AssignmentNotification.objects.all().delete()
    enrollment = Enrollment.objects.get(course=course)
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=ct3)
    create_notifications_about_new_submission(comment)
    notifications = (AssignmentNotification.objects
                     .filter(student_assignment=student_assignment))
    assert notifications.count() == 1
    assert notifications[0].user == ct3.teacher
