from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.timezone import now

from core.tests.factories import BranchFactory
from courses.constants import AssigneeMode
from courses.models import CourseTeacher, StudentGroupTypes
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.models import (
    AssignmentNotification, Enrollment, StudentAssignment, StudentGroup, EnrollmentGradeLog
)
from learning.services import AssignmentService
from learning.services.enrollment_service import update_enrollment_grade
from learning.services.notification_service import (
    create_notifications_about_new_submission
)
from learning.settings import Branches, StudentStatuses, GradeTypes, EnrollmentGradeUpdateSource
from learning.tests.factories import (
    AssignmentCommentFactory, AssignmentNotificationFactory, EnrollmentFactory,
    StudentAssignmentFactory, StudentGroupAssigneeFactory
)
from users.tests.factories import StudentProfileFactory, StudentFactory, CuratorFactory, TeacherFactory


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
def test_assignment_service_bulk_create_personal_assignments_notifications(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    enrollment1, enrollment2, enrollment3 = EnrollmentFactory.create_batch(3, course=course)
    assignment = AssignmentFactory(course=course)
    StudentAssignment.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert AssignmentNotification.objects.count() == 3
    # 1 already exist
    StudentAssignment.objects.all().delete()
    AssignmentService.create_or_restore_student_assignment(assignment, enrollment1)
    AssignmentNotification.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert AssignmentNotification.objects.count() == 2
    # 1 exist, 1 soft deleted
    StudentAssignment.objects.all().delete()
    AssignmentService.create_or_restore_student_assignment(assignment, enrollment1)
    student_assignment2 = AssignmentService.create_or_restore_student_assignment(assignment, enrollment2)
    student_assignment2.delete()
    assert student_assignment2.is_deleted
    AssignmentNotification.objects.all().delete()
    AssignmentService.bulk_create_student_assignments(assignment)
    assert AssignmentNotification.objects.count() == 2


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
    course = CourseFactory()
    assignment = AssignmentFactory(course=course, assignee_mode=AssigneeMode.MANUAL)
    student_assignment = StudentAssignmentFactory(assignment=assignment)
    comment = AssignmentCommentFactory(author=student_assignment.student,
                                       student_assignment=student_assignment)
    AssignmentNotification.objects.all().delete()
    create_notifications_about_new_submission(comment)
    assert AssignmentNotification.objects.count() == 0
    # Add first course teacher
    course_teacher1 = CourseTeacherFactory(course=course, roles=CourseTeacher.roles.lecturer)
    create_notifications_about_new_submission(comment)
    assert AssignmentNotification.objects.count() == 0
    # Add course teachers with a reviewer role and mark them as responsible
    course_teacher2 = CourseTeacherFactory(course=course,
                                           roles=CourseTeacher.roles.reviewer,
                                           notify_by_default=True)
    course_teacher3 = CourseTeacherFactory(course=course,
                                           roles=CourseTeacher.roles.reviewer,
                                           notify_by_default=True)
    assignment.assignees.add(course_teacher2, course_teacher3)
    create_notifications_about_new_submission(comment)
    assert AssignmentNotification.objects.count() == 2
    # Assign student assignment to teacher
    student_assignment.assignee = course_teacher2
    student_assignment.save()
    AssignmentNotification.objects.all().delete()
    create_notifications_about_new_submission(comment)
    notifications = (AssignmentNotification.objects
                     .filter(student_assignment=student_assignment))
    assert notifications.count() == 1
    assert notifications[0].user == course_teacher2.teacher
    student_assignment.assignee = None
    student_assignment.save()
    # Set responsible teachers for the student group
    AssignmentNotification.objects.all().delete()
    enrollment = Enrollment.objects.get(course=course)
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher3)
    assignment.assignee_mode = AssigneeMode.STUDENT_GROUP_DEFAULT
    assignment.save()
    create_notifications_about_new_submission(comment)
    notifications = (AssignmentNotification.objects
                     .filter(student_assignment=student_assignment))
    assert notifications.count() == 1
    assert notifications[0].user == course_teacher3.teacher
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher2)
    AssignmentNotification.objects.all().delete()
    create_notifications_about_new_submission(comment)
    notifications = (AssignmentNotification.objects
                     .filter(student_assignment=student_assignment))
    assert notifications.count() == 2


@pytest.mark.django_db
def test_update_enrollment_grade_permissions():
    student = StudentFactory()

    enrollment = EnrollmentFactory(student=student)

    grade_changed_at = now()
    with pytest.raises(PermissionDenied):
        update_enrollment_grade(enrollment=enrollment,
                                old_grade=enrollment.grade,
                                new_grade=GradeTypes.EXCELLENT,
                                editor=student,
                                grade_changed_at=grade_changed_at,
                                source=EnrollmentGradeUpdateSource.GRADEBOOK)

    curator = CuratorFactory()
    update_enrollment_grade(enrollment=enrollment,
                            old_grade=enrollment.grade,
                            new_grade=GradeTypes.EXCELLENT,
                            editor=curator,
                            grade_changed_at=grade_changed_at,
                            source=EnrollmentGradeUpdateSource.GRADEBOOK)
    enrollment.refresh_from_db()
    assert enrollment.grade == GradeTypes.EXCELLENT
    logs = EnrollmentGradeLog.objects.all()
    assert logs.count() == 1
    log = logs.first()
    assert log.grade == GradeTypes.EXCELLENT
    assert log.entry_author == curator
    assert log.grade_changed_at == grade_changed_at
    assert log.source == EnrollmentGradeUpdateSource.GRADEBOOK

    teacher, another_teacher, spectator = TeacherFactory.create_batch(3)
    CourseTeacherFactory(teacher=teacher, course=enrollment.course)
    update_enrollment_grade(enrollment=enrollment,
                            old_grade=enrollment.grade,
                            new_grade=GradeTypes.CREDIT,
                            editor=teacher,
                            grade_changed_at=grade_changed_at,
                            source=EnrollmentGradeUpdateSource.GRADEBOOK)
    enrollment.refresh_from_db()
    assert enrollment.grade == GradeTypes.CREDIT  # changed in db

    with pytest.raises(PermissionDenied):
        CourseTeacherFactory(teacher=another_teacher, course=CourseFactory())
        update_enrollment_grade(enrollment=enrollment,
                                old_grade=enrollment.grade,
                                new_grade=GradeTypes.GOOD,
                                editor=another_teacher,
                                grade_changed_at=grade_changed_at,
                                source=EnrollmentGradeUpdateSource.GRADEBOOK)

    CourseTeacherFactory(teacher=spectator, course=enrollment.course,
                         roles=CourseTeacher.roles.spectator)
    with pytest.raises(PermissionDenied) as e:
        CourseTeacherFactory(teacher=another_teacher, course=CourseFactory())
        update_enrollment_grade(enrollment=enrollment,
                                old_grade=enrollment.grade,
                                new_grade=GradeTypes.GOOD,
                                editor=spectator,
                                grade_changed_at=grade_changed_at,
                                source=EnrollmentGradeUpdateSource.GRADEBOOK)


@pytest.mark.django_db
def test_update_enrollment_grade_validation():
    enrollment = EnrollmentFactory()
    curator = CuratorFactory()

    with pytest.raises(ValidationError):
        update_enrollment_grade(enrollment=enrollment,
                                old_grade=enrollment.grade,
                                new_grade='incorrect grade',
                                editor=curator,
                                source=EnrollmentGradeUpdateSource.GRADEBOOK)

    with pytest.raises(ValidationError):
        update_enrollment_grade(enrollment=enrollment,
                                old_grade=enrollment.grade,
                                new_grade=GradeTypes.GOOD,
                                editor=curator,
                                source='incorrect source')


@pytest.mark.django_db
def test_update_enrollment_grade_concurrency():
    enrollment = EnrollmentFactory()
    curator = CuratorFactory()

    updated, _ = update_enrollment_grade(enrollment=enrollment,
                                         old_grade=enrollment.grade,
                                         new_grade=GradeTypes.GOOD,
                                         editor=curator,
                                         source=EnrollmentGradeUpdateSource.GRADEBOOK)
    assert updated
    assert enrollment.grade == GradeTypes.GOOD  # changed on instance level
    enrollment.refresh_from_db()
    assert enrollment.grade == GradeTypes.GOOD  # changed in db
    logs = EnrollmentGradeLog.objects.all()
    assert logs.count() == 1
    log = logs.first()
    assert log.grade == GradeTypes.GOOD

    updated, _ = update_enrollment_grade(enrollment=enrollment,
                                         old_grade=GradeTypes.CREDIT,
                                         new_grade=GradeTypes.EXCELLENT,
                                         editor=curator,
                                         source=EnrollmentGradeUpdateSource.GRADEBOOK)
    assert not updated
    assert enrollment.grade == GradeTypes.GOOD  # not changed on instance level
    enrollment.refresh_from_db()
    assert enrollment.grade == GradeTypes.GOOD  # not changed in db
    logs = EnrollmentGradeLog.objects.all()
    assert logs.count() == 1  # there is no new logs

    # External grade change
    (Enrollment.objects.
        filter(pk=enrollment.pk)
        .update(grade=GradeTypes.CREDIT))
    enrollment.grade = GradeTypes.UNSATISFACTORY
    updated, _ = update_enrollment_grade(enrollment=enrollment,
                                         old_grade=GradeTypes.CREDIT,
                                         new_grade=GradeTypes.EXCELLENT,
                                         editor=curator,
                                         source=EnrollmentGradeUpdateSource.GRADEBOOK)
    assert updated
    assert enrollment.grade == GradeTypes.EXCELLENT  # instance value has been changed
    enrollment.refresh_from_db()
    assert enrollment.grade == GradeTypes.EXCELLENT  # db values has been changed
    logs = EnrollmentGradeLog.objects.all()
    assert logs.count() == 2

    # instance value is correct, but old_grade argument not
    updated, _ = update_enrollment_grade(enrollment=enrollment,
                                         old_grade=GradeTypes.RE_CREDIT,
                                         new_grade=GradeTypes.CREDIT,
                                         editor=curator,
                                         source=EnrollmentGradeUpdateSource.GRADEBOOK)
    assert not updated
    assert enrollment.grade == GradeTypes.EXCELLENT  # instance value has been changed
    enrollment.refresh_from_db()
    assert enrollment.grade == GradeTypes.EXCELLENT  # db values has been changed
    logs = EnrollmentGradeLog.objects.all()
    assert logs.count() == 2
