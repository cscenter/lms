import pytest

from courses.constants import AssigneeMode, AssignmentFormat, AssignmentStatuses
from courses.models import CourseGroupModes, CourseTeacher
from courses.tests.factories import AssignmentFactory, CourseFactory
from learning.models import Enrollment, PersonalAssignmentActivity, StudentAssignment, AssignmentSubmissionTypes
from learning.services import EnrollmentService
from learning.services.personal_assignment_service import (
    create_assignment_comment, resolve_assignees_for_personal_assignment, update_personal_assignment_status,
    create_assignment_solution
)
from learning.tests.factories import (
    AssignmentCommentFactory, EnrollmentFactory, StudentAssignmentFactory,
    StudentGroupAssigneeFactory, StudentGroupFactory
)
from users.services import get_student_profile
from users.tests.factories import CuratorFactory, StudentFactory, TeacherFactory


@pytest.mark.django_db
def test_resolve_assignees_for_personal_assignment(settings):
    teacher1, teacher2 = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher1, teacher2], group_mode=CourseGroupModes.MANUAL)
    assignment = AssignmentFactory(course=course, assignee_mode=AssigneeMode.DISABLED)
    course_teacher1, course_teacher2 = CourseTeacher.objects.filter(course=course)
    student_assignment = StudentAssignmentFactory(assignment=assignment, assignee=None)
    # Disabled mode
    student_assignment.assignee = course_teacher1
    assert resolve_assignees_for_personal_assignment(student_assignment) == [course_teacher1]
    student_assignment.assignee = None
    assert not resolve_assignees_for_personal_assignment(student_assignment)
    # Manual mode
    assignment.assignee_mode = AssigneeMode.MANUAL
    assignment.save()
    assignment.assignees.clear()
    assert len(resolve_assignees_for_personal_assignment(student_assignment)) == 0
    assignment.assignees.add(course_teacher1, course_teacher2)
    teachers = resolve_assignees_for_personal_assignment(student_assignment)
    assert len(teachers) == 2
    assert course_teacher1 in teachers
    assert course_teacher2 in teachers
    assignment.assignees.clear()
    assignment.assignees.add(course_teacher1)
    assert resolve_assignees_for_personal_assignment(student_assignment) == [course_teacher1]
    # Student Group Default
    student_group = StudentGroupFactory(course=course)
    assignment.assignee_mode = AssigneeMode.STUDENT_GROUP_DEFAULT
    assignment.save()
    enrollment = Enrollment.objects.get(student=student_assignment.student)
    enrollment.delete()
    with pytest.raises(Enrollment.DoesNotExist):
        resolve_assignees_for_personal_assignment(student_assignment)
    student_profile = get_student_profile(user=student_assignment.student, site=settings.SITE_ID)
    EnrollmentService.enroll(student_profile, course, student_group=student_group)
    assert not resolve_assignees_for_personal_assignment(student_assignment)
    assert not resolve_assignees_for_personal_assignment(student_assignment)
    sga = StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher1)
    assert resolve_assignees_for_personal_assignment(student_assignment) == [course_teacher1]
    # Student Group Custom
    StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher2, assignment=assignment)
    assert resolve_assignees_for_personal_assignment(student_assignment) == [course_teacher1]
    assignment.assignee_mode = AssigneeMode.STUDENT_GROUP_CUSTOM
    assignment.save()
    assert resolve_assignees_for_personal_assignment(student_assignment) == [course_teacher2]
    StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher1, assignment=assignment)
    assert len(resolve_assignees_for_personal_assignment(student_assignment)) == 2


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
def test_maybe_set_assignee_for_personal_assignment():
    student = StudentFactory()
    teacher1, teacher2 = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher1, teacher2])
    course_teacher1, course_teacher2 = CourseTeacher.objects.filter(course=course)
    assignment = AssignmentFactory(course=course,
                                   assignee_mode=AssigneeMode.STUDENT_GROUP_DEFAULT)
    student_assignment = StudentAssignmentFactory(assignment=assignment, student=student)
    # Don't trigger on teacher's activity
    comment1 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=teacher1)
    student_assignment.refresh_from_db()
    assert student_assignment.assignee is None
    assert student_assignment.trigger_auto_assign is True
    # Assign teacher responsible for the student group
    enrollment = Enrollment.objects.get(student=comment1.student_assignment.student)
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher1)
    comment2 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is False
    assert student_assignment.assignee == course_teacher1
    # Auto assigning doesn't work if enrollment is deleted
    EnrollmentService.leave(enrollment)
    student_assignment.trigger_auto_assign = True
    student_assignment.assignee = None
    student_assignment.save()
    comment3 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is True
    # Multiple responsible teachers for the group
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher2)
    enrollment.is_deleted = False
    enrollment.save()
    AssignmentCommentFactory(student_assignment=student_assignment, author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is False
    assert student_assignment.assignee is None
    # Stale customized settings for the assignment have no effect
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher1,
                                assignment=assignment)
    student_assignment.trigger_auto_assign = True
    student_assignment.assignee = None
    student_assignment.save()
    AssignmentCommentFactory(student_assignment=student_assignment, author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is False
    assert student_assignment.assignee is None
    # Change assignee mode
    assignment.assignee_mode = AssigneeMode.STUDENT_GROUP_CUSTOM
    assignment.save()
    student_assignment.trigger_auto_assign = True
    student_assignment.assignee = None
    student_assignment.save()
    AssignmentCommentFactory(student_assignment=student_assignment, author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is False
    assert student_assignment.assignee == course_teacher1


@pytest.mark.django_db
def test_create_assignment_solution_changes_status():
    sa = StudentAssignmentFactory(assignment__submission_type=AssignmentFormat.ONLINE)
    student = sa.student
    assert sa.status == AssignmentStatuses.NOT_SUBMITTED
    create_assignment_solution(personal_assignment=sa,
                               created_by=student,
                               message="solution")
    sa.refresh_from_db()
    assert sa.status == AssignmentStatuses.ON_CHECKING


@pytest.mark.django_db
def test_update_personal_assignment_status():
    sa = StudentAssignmentFactory(assignment__submission_type=AssignmentFormat.NO_SUBMIT)

    assert sa.status == AssignmentStatuses.NOT_SUBMITTED
    updated, _ = update_personal_assignment_status(student_assignment=sa,
                                                   status_old=AssignmentStatuses.NOT_SUBMITTED,
                                                   status_new=AssignmentStatuses.NOT_SUBMITTED)
    sa.refresh_from_db()
    assert updated

    # testing case when status_old is wrong
    updated, _ = update_personal_assignment_status(student_assignment=sa,
                                                   status_old=AssignmentStatuses.ON_CHECKING,
                                                   status_new=AssignmentStatuses.NOT_SUBMITTED)
    assert not updated

    # submission is needed for the next test
    AssignmentCommentFactory(student_assignment=sa,
                             type=AssignmentSubmissionTypes.SOLUTION)
    sa.refresh_from_db()
    # it changes status automatically
    assert sa.status == AssignmentStatuses.ON_CHECKING

    # test forbidden statuses
    with pytest.raises(ValueError):
        # status NOT_SUBMITTED not allowed if submission exists
        update_personal_assignment_status(student_assignment=sa,
                                          status_old=AssignmentStatuses.ON_CHECKING,
                                          status_new=AssignmentStatuses.NOT_SUBMITTED)
    with pytest.raises(ValueError):
        # NEED_FIXES not allowed for NO_SUBMIT assignment format
        update_personal_assignment_status(student_assignment=sa,
                                          status_old=AssignmentStatuses.ON_CHECKING,
                                          status_new=AssignmentStatuses.NEED_FIXES)

    updated, _ = update_personal_assignment_status(student_assignment=sa,
                                                   status_old=AssignmentStatuses.ON_CHECKING,
                                                   status_new=AssignmentStatuses.COMPLETED)
    sa.refresh_from_db()
    assert updated
    assert sa.status == AssignmentStatuses.COMPLETED

    sa = StudentAssignmentFactory(assignment__submission_type=AssignmentFormat.ONLINE)
    AssignmentCommentFactory(student_assignment=sa,
                             type=AssignmentSubmissionTypes.SOLUTION)
    sa.refresh_from_db()
    # NEED_FIXES allowed for ONLINE assignment format
    updated, _ = update_personal_assignment_status(student_assignment=sa,
                                                   status_old=AssignmentStatuses.ON_CHECKING,
                                                   status_new=AssignmentStatuses.NEED_FIXES)
    sa.refresh_from_db()
    assert updated
    assert sa.status == AssignmentStatuses.NEED_FIXES

