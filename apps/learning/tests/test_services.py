from datetime import timedelta

import pytest

from core.tests.factories import BranchFactory
from courses.models import CourseTeacher, StudentGroupTypes
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.models import (
    AssignmentNotification, Enrollment, PersonalAssignmentActivity, StudentAssignment,
    StudentGroup
)
from learning.services import (
    AssignmentService, create_assignment_comment,
    create_notifications_about_new_submission
)
from learning.settings import Branches, StudentStatuses
from learning.tests.factories import (
    AssignmentCommentFactory, AssignmentNotificationFactory, EnrollmentFactory,
    StudentAssignmentFactory, StudentGroupAssigneeFactory
)
from users.models import StudentTypes, UserGroup
from users.services import StudentProfileError, create_student_profile
from users.tests.factories import (
    CuratorFactory, StudentFactory, StudentProfileFactory, TeacherFactory, UserFactory
)


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
def test_assignment_service_bulk_create_personal_assignments(settings):
    branch_spb = BranchFactory(code="spb")
    branch_nsk = BranchFactory(code="nsk")
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
def test_assignment_service_create_personal_assignments_inactive_status(inactive_status, settings):
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
def test_assignment_service_bulk_create_personal_assignments_with_existing_records(settings):
    """
    Create personal assignments for assignment where some personal records
    already exist.
    """
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    enrollment1, enrollment2, enrollment3 = EnrollmentFactory.create_batch(3, course=course)
    student_profile1 = enrollment1.student_profile
    assignment = AssignmentFactory(course=course)
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 3
    StudentAssignment.objects.filter(assignment=assignment, student=student_profile1.user).delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert StudentAssignment.objects.filter(assignment=assignment).count() == 3


@pytest.mark.django_db
def test_assignment_service_remove_personal_assignments():
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
def test_assignment_service_sync_personal_assignments():
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


@pytest.mark.django_db
def test_maybe_set_assignee_for_personal_assignment():
    student = StudentFactory()
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  student=student)
    # Don't trigger on teacher activity
    comment1 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=teacher)
    student_assignment.refresh_from_db()
    assert student_assignment.assignee is None
    assert student_assignment.trigger_auto_assign is True
    # Assign teacher responsible for the student group
    enrollment = Enrollment.objects.get(student=comment1.student_assignment.student)
    course_teacher = CourseTeacher.objects.get(course=course)
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher)
    comment2 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is False
    assert student_assignment.assignee == course_teacher
    # Auto assigning doesn't work if enrollment is deleted
    enrollment.is_deleted = True
    enrollment.save()
    student_assignment.trigger_auto_assign = True
    student_assignment.assignee = None
    student_assignment.save()
    comment3 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is True


@pytest.mark.django_db
def test_maybe_set_assignee_for_personal_assignment_already_assigned():
    """Don't overwrite assignee if someone was set before student activity."""
    teacher1, teacher2 = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher1, teacher2])
    course_teacher1 = CourseTeacher.objects.get(course=course, teacher=teacher1)
    course_teacher2 = CourseTeacher.objects.get(course=course, teacher=teacher2)
    student = StudentFactory()
    enrollment = EnrollmentFactory(course=course, student=student)
    # Teacher2 is responsible fot the student group
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher2)
    # But teacher1 was assigned before student activity
    assignment = AssignmentFactory(course=course)
    student_assignment = StudentAssignment.objects.get(student=student)
    student_assignment.assignee = course_teacher1
    student_assignment.save()
    # Leave a comment from the student
    AssignmentCommentFactory(student_assignment=student_assignment,
                             author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.assignee == course_teacher1
    assert student_assignment.trigger_auto_assign is False


@pytest.mark.django_db
def test_update_personal_assignment_stats():
    curator = CuratorFactory()
    student_assignment = StudentAssignmentFactory()
    create_assignment_comment(personal_assignment=student_assignment,
                              is_draft=True,
                              created_by=curator,
                              message='Comment message')
    student_assignment.refresh_from_db()
    assert student_assignment.meta is None
    comment = create_assignment_comment(personal_assignment=student_assignment,
                                        is_draft=False,
                                        created_by=curator,
                                        message='Comment message')
    student_assignment.refresh_from_db()
    assert isinstance(student_assignment.meta, dict)
    assert student_assignment.meta['stats']['comments'] == 1
    assert student_assignment.meta['stats']['activity']['code'] == PersonalAssignmentActivity.TEACHER_COMMENT
