from datetime import timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Set

import pytest

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

from courses.constants import AssigneeMode, AssignmentFormat, AssignmentStatus
from courses.models import CourseGroupModes, CourseTeacher
from courses.tests.factories import AssignmentFactory, CourseFactory, CourseTeacherFactory
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment,
    PersonalAssignmentActivity, StudentAssignment, StudentGroupTeacherBucket
)
from learning.services import EnrollmentService, StudentGroupService
from learning.services.personal_assignment_service import (
    create_assignment_comment, create_assignment_solution,
    create_personal_assignment_review, resolve_assignees_for_personal_assignment,
    update_personal_assignment_score, update_personal_assignment_stats,
    update_personal_assignment_status, get_assignee_with_minimal_load,
    calculate_teachers_overall_expected_load_in_bucket
)
from learning.settings import AssignmentScoreUpdateSource
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
def test_service_update_personal_assignment_stats_unpublished():
    """Do not calculate stats for a draft submission."""
    curator = CuratorFactory()
    student_assignment = StudentAssignmentFactory()
    create_assignment_comment(personal_assignment=student_assignment,
                              is_draft=True,
                              created_by=curator,
                              message='Comment message')
    student_assignment.refresh_from_db()
    assert student_assignment.meta is None


@pytest.mark.django_db
def test_service_update_personal_assignment_stats_published(django_capture_on_commit_callbacks):
    curator = CuratorFactory()
    student_assignment = StudentAssignmentFactory()
    with django_capture_on_commit_callbacks(execute=True):
        comment1 = create_assignment_comment(personal_assignment=student_assignment,
                                             is_draft=False,
                                             created_by=curator,
                                             message='Comment1 message')
    student_assignment.refresh_from_db()
    assert isinstance(student_assignment.meta, dict)
    assert student_assignment.meta['stats']['comments'] == 1
    assert student_assignment.meta['stats']['activity'] == PersonalAssignmentActivity.TEACHER_COMMENT
    assert "solutions" not in student_assignment.meta['stats']
    solution1 = create_assignment_solution(personal_assignment=student_assignment,
                                           created_by=student_assignment.student,
                                           message="solution")
    update_personal_assignment_stats(personal_assignment=student_assignment)
    student_assignment.refresh_from_db()
    assert student_assignment.stats['activity'] == PersonalAssignmentActivity.SOLUTION
    assert student_assignment.stats['comments'] == 1
    assert 'solutions' in student_assignment.stats
    solutions_stats = student_assignment.stats['solutions']
    assert 'count' in solutions_stats
    assert solutions_stats['count'] == 1
    assert 'first' in solutions_stats
    assert solutions_stats['first'] == solution1.created.replace(microsecond=0)
    assert 'last' in solutions_stats
    assert solutions_stats['last'] == solution1.created.replace(microsecond=0)
    # Emulate `late` stats processing
    solution2 = create_assignment_solution(personal_assignment=student_assignment,
                                           created_by=student_assignment.student,
                                           message="solution2")
    fixed_dt = solution2.created + timedelta(minutes=2)
    AssignmentComment.objects.filter(pk=solution2.pk).update(created=fixed_dt)
    comment2 = create_assignment_comment(personal_assignment=student_assignment,
                                         is_draft=False,
                                         created_by=curator,
                                         message='Comment2 message')
    solution2.refresh_from_db()
    assert solution2.created > comment2.created
    update_personal_assignment_stats(personal_assignment=student_assignment)
    student_assignment.refresh_from_db()
    assert student_assignment.stats['comments'] == 2
    assert student_assignment.stats['activity'] == PersonalAssignmentActivity.SOLUTION
    assert 'solutions' in student_assignment.stats
    solutions_stats = student_assignment.stats['solutions']
    assert 'count' in solutions_stats
    assert solutions_stats['count'] == 2
    assert 'first' in solutions_stats
    delta = timedelta(seconds=1)
    assert comment1.created - delta <= solutions_stats['first'] <= comment1.created + delta
    assert 'last' in solutions_stats
    assert fixed_dt - delta <= solutions_stats['last'] <= fixed_dt + delta


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
    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    create_assignment_solution(personal_assignment=sa,
                               created_by=student,
                               message="solution")
    sa.refresh_from_db()
    assert sa.status == AssignmentStatus.ON_CHECKING


@pytest.mark.django_db
def test_update_personal_assignment_status(django_capture_on_commit_callbacks):
    sa = StudentAssignmentFactory(assignment__submission_type=AssignmentFormat.NO_SUBMIT)

    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    updated = update_personal_assignment_status(student_assignment=sa,
                                                status_old=AssignmentStatus.NOT_SUBMITTED,
                                                status_new=AssignmentStatus.NOT_SUBMITTED)
    sa.refresh_from_db()
    assert updated

    # testing case when status_old is wrong
    updated = update_personal_assignment_status(student_assignment=sa,
                                                status_old=AssignmentStatus.ON_CHECKING,
                                                status_new=AssignmentStatus.NOT_SUBMITTED)
    assert not updated

    # fake status change is not successful if db value was changed
    sa.status = AssignmentStatus.ON_CHECKING
    sa.save()
    # fake: status_old == status_new, so db update is not required
    updated = update_personal_assignment_status(student_assignment=sa,
                                                status_old=AssignmentStatus.NOT_SUBMITTED,
                                                status_new=AssignmentStatus.NOT_SUBMITTED)
    # it's not successful because because db_status != status_old
    assert not updated
    assert sa.status == AssignmentStatus.ON_CHECKING
    sa.status = AssignmentStatus.NOT_SUBMITTED
    sa.save()

    # submission is needed for the next test
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        AssignmentCommentFactory(student_assignment=sa,
                                 type=AssignmentSubmissionTypes.SOLUTION)
    assert len(callbacks) == 1
    sa.refresh_from_db()
    # it changes status automatically
    assert sa.status == AssignmentStatus.ON_CHECKING

    # test forbidden statuses
    with pytest.raises(ValidationError):
        # status NOT_SUBMITTED not allowed if submission exists
        update_personal_assignment_status(student_assignment=sa,
                                          status_old=AssignmentStatus.ON_CHECKING,
                                          status_new=AssignmentStatus.NOT_SUBMITTED)
    with pytest.raises(ValidationError):
        # NEED_FIXES not allowed for NO_SUBMIT assignment format
        update_personal_assignment_status(student_assignment=sa,
                                          status_old=AssignmentStatus.ON_CHECKING,
                                          status_new=AssignmentStatus.NEED_FIXES)

    updated = update_personal_assignment_status(student_assignment=sa,
                                                status_old=AssignmentStatus.ON_CHECKING,
                                                status_new=AssignmentStatus.COMPLETED)
    sa.refresh_from_db()
    assert updated
    assert sa.status == AssignmentStatus.COMPLETED

    sa = StudentAssignmentFactory(assignment__submission_type=AssignmentFormat.ONLINE)
    AssignmentCommentFactory(student_assignment=sa,
                             type=AssignmentSubmissionTypes.SOLUTION)
    sa.refresh_from_db()
    # NEED_FIXES allowed for ONLINE assignment format
    updated = update_personal_assignment_status(student_assignment=sa,
                                                status_old=AssignmentStatus.ON_CHECKING,
                                                status_new=AssignmentStatus.NEED_FIXES)
    sa.refresh_from_db()
    assert updated
    assert sa.status == AssignmentStatus.NEED_FIXES


@pytest.mark.django_db
def test_create_assignment_comment_empty():
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course)
    with pytest.raises(ValidationError):
        create_assignment_comment(personal_assignment=sa, message="",
                                  is_draft=True, created_by=teacher)
    with pytest.raises(ValidationError):
        create_assignment_comment(personal_assignment=sa, message="",
                                  is_draft=False, created_by=teacher)
    create_assignment_comment(personal_assignment=sa, message="",
                              is_draft=True, created_by=teacher,
                              attachment=SimpleUploadedFile("1", b""))
    assert AssignmentComment.objects.filter(is_published=False).count() == 1

    comment = create_assignment_comment(personal_assignment=sa, message="",
                                        is_draft=False, created_by=teacher,
                                        attachment=SimpleUploadedFile("2", b""))
    assert AssignmentComment.objects.filter(is_published=False).count() == 0
    assert AssignmentComment.objects.filter(is_published=True).count() == 1
    comment.delete()


@pytest.mark.django_db
def test_create_assignment_comment_with_meta():
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course)

    comment = create_assignment_comment(personal_assignment=sa, message="",
                                        is_draft=True, created_by=teacher,
                                        meta={"status": AssignmentStatus.NOT_SUBMITTED})
    assert AssignmentComment.objects.filter(is_published=False).count() == 1
    assert comment.meta['status'] == AssignmentStatus.NOT_SUBMITTED
    assert 'score' not in comment.meta
    with pytest.raises(ValidationError):
        comment = create_assignment_comment(personal_assignment=sa, message="",
                                            is_draft=False, created_by=teacher,
                                            meta={"status": AssignmentStatus.NOT_SUBMITTED})
    comment = create_assignment_comment(personal_assignment=sa, message="",
                                        is_draft=False, created_by=teacher,
                                        meta={
                                            "status": AssignmentStatus.NOT_SUBMITTED,
                                            "status_old": sa.status
                                        })
    assert AssignmentComment.objects.filter(is_published=True).count() == 1
    assert AssignmentComment.objects.filter(is_published=False).count() == 0
    comment.delete()

    comment = create_assignment_comment(personal_assignment=sa, message="",
                                        is_draft=True,
                                        created_by=teacher,
                                        meta={"score": None})
    assert AssignmentComment.objects.filter(is_published=False).count() == 1
    assert comment.meta['score'] == None
    assert 'status' not in comment.meta
    comment.delete()

    comment = create_assignment_comment(personal_assignment=sa, message="",
                                        is_draft=True,
                                        created_by=teacher,
                                        meta={"score": Decimal('0')})
    assert AssignmentComment.objects.filter(is_published=False).count() == 1
    assert comment.meta['score'] == 0
    assert 'status' not in comment.meta


# TODO: write full test for update method
@pytest.mark.django_db
def test_update_personal_assignment_score_fake_update():
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course)
    # fake: score_old  == score_new, so DB updating is not required
    updated, _ = update_personal_assignment_score(student_assignment=sa,
                                                  score_old=Decimal('0'),
                                                  score_new=Decimal('0'),
                                                  changed_by=teacher,
                                                  source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT)
    # it's not successful because db_score != score_old
    assert not updated
    assert sa.score is None


@pytest.mark.django_db
def test_create_personal_assignment_review(django_capture_on_commit_callbacks):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course,
                                  assignment__maximum_score=5)

    # Nothing to update
    with pytest.raises(ValidationError) as exc_info:
        create_personal_assignment_review(student_assignment=sa,
                                          reviewer=teacher,
                                          is_draft=False,
                                          message="",
                                          score_old=sa.score,
                                          score_new=sa.score,
                                          status_old=sa.status,
                                          status_new=sa.status,
                                          source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                          )
    assert exc_info.value.code == 'empty'
    assert AssignmentComment.objects.count() == 0

    # Only the message has been provided
    comment = create_personal_assignment_review(student_assignment=sa,
                                                reviewer=teacher,
                                                is_draft=False,
                                                message="Some message",
                                                score_old=sa.score,
                                                score_new=sa.score,
                                                status_old=sa.status,
                                                status_new=sa.status,
                                                source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                                )
    assert comment.is_published
    assert comment.text == "Some message"
    assert comment.meta['score'] == sa.score
    assert comment.meta['status'] == sa.status

    # Only the score has been changed.
    comment = create_personal_assignment_review(student_assignment=sa,
                                                reviewer=teacher,
                                                is_draft=False,
                                                message="",
                                                score_old=sa.score,
                                                score_new=Decimal('0'),
                                                status_old=sa.status,
                                                status_new=sa.status,
                                                source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                                )
    assert comment.is_published
    assert comment.text == ""
    assert comment.meta['score'] == 0
    assert comment.meta['status'] == sa.status

    # Only the status has been changed.
    comment = create_personal_assignment_review(student_assignment=sa,
                                                reviewer=teacher,
                                                is_draft=False,
                                                message="",
                                                score_old=sa.score,
                                                score_new=sa.score,
                                                status_old=sa.status,
                                                status_new=AssignmentStatus.NEED_FIXES,
                                                source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                                )
    assert comment.is_published
    assert comment.text == ""
    assert comment.meta['score'] == 0
    assert comment.meta['status'] == AssignmentStatus.NEED_FIXES

    # Only the file has been provided.
    comment = create_personal_assignment_review(student_assignment=sa,
                                                reviewer=teacher,
                                                is_draft=False,
                                                message="",
                                                attachment=SimpleUploadedFile("1", b"hello world"),
                                                score_old=sa.score,
                                                score_new=sa.score,
                                                status_old=sa.status,
                                                status_new=sa.status,
                                                source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                                )
    assert comment.is_published
    assert comment.text == ""
    assert b"hello world" in comment.attached_file
    assert comment.meta['score'] == 0
    assert comment.meta['status'] == AssignmentStatus.NEED_FIXES

    assert AssignmentComment.objects.count() == 4
    AssignmentComment.objects.all().delete()

    #  Score overflow
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Some text",
                                              score_old=sa.score,
                                              score_new=Decimal('6'),
                                              status_old=sa.status,
                                              status_new=AssignmentStatus.COMPLETED,
                                              source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                              )
    sa.refresh_from_db()  # atomic doesn't restore state
    assert exc_info.value.code == 'score_overflow'
    assert sa.score != 6
    assert sa.status != AssignmentStatus.COMPLETED
    assert AssignmentComment.objects.count() == 0

    # Update personal assignment status to `on_checking`
    with django_capture_on_commit_callbacks(execute=True):
        create_assignment_solution(personal_assignment=sa,
                                   created_by=sa.student,
                                   message="solution")
    sa.refresh_from_db()
    # Create review with a forbidden status
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Some text",
                                              score_old=sa.score,
                                              score_new=Decimal('5'),
                                              status_old=sa.status,
                                              status_new=AssignmentStatus.NOT_SUBMITTED,
                                              source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                              )
    sa.refresh_from_db()
    assert exc_info.value.code == 'status_not_allowed'
    assert sa.score != 5
    assert sa.status != AssignmentStatus.NOT_SUBMITTED
    assert AssignmentComment.objects.exclude(author=sa.student).count() == 0

    # TODO: add negative score value test


@pytest.mark.django_db
def test_create_personal_assignment_review_concurrent_update():
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course,
                                  assignment__maximum_score=5)
    # Irrelevant score_old
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Irrelevant score_old != score_new",
                                              score_old=Decimal('3'),
                                              score_new=Decimal('5'),
                                              status_old=sa.status,
                                              status_new=AssignmentStatus.NEED_FIXES,
                                              source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                              )
    assert exc_info.value.code == 'concurrent'
    sa.refresh_from_db()
    assert sa.score is None
    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    assert AssignmentComment.objects.count() == 0

    # Fake score update
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Irrelevant score_old == score_new",
                                              score_old=Decimal('0'),
                                              score_new=Decimal('0'),
                                              status_old=sa.status,
                                              status_new=AssignmentStatus.NEED_FIXES,
                                              source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                              )
    assert exc_info.value.code == 'concurrent'
    sa.refresh_from_db()
    assert sa.score is None
    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    assert AssignmentComment.objects.count() == 0

    # Irrelevant status_old
    sa.refresh_from_db()
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Irrelevant status_old != new_status",
                                              score_old=sa.score,
                                              score_new=Decimal('5'),
                                              status_old=AssignmentStatus.COMPLETED,
                                              status_new=AssignmentStatus.NEED_FIXES,
                                              source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                              )
    assert exc_info.value.code == 'concurrent'
    sa.refresh_from_db()
    assert sa.score is None
    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    assert AssignmentComment.objects.count() == 0

    # Fake status update
    sa.refresh_from_db()
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Irrelevant status_old == new_status",
                                              score_old=sa.score,
                                              score_new=Decimal('5'),
                                              status_old=AssignmentStatus.NEED_FIXES,
                                              status_new=AssignmentStatus.NEED_FIXES,
                                              source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
                                              )
    assert exc_info.value.code == 'concurrent'
    sa.refresh_from_db()
    assert sa.score is None
    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    assert AssignmentComment.objects.count() == 0


@pytest.mark.django_db
def test_create_assignment_comment_meta():
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course,
                                  assignment__maximum_score=5)
    comment = create_personal_assignment_review(
        student_assignment=sa,
        is_draft=False,
        reviewer=teacher,
        message="",
        score_old=sa.score,
        status_old=sa.status,
        score_new=Decimal('1'),
        status_new=AssignmentStatus.ON_CHECKING,
        source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
    )
    assert comment.meta == {
        "score": Decimal('1'),
        "status": AssignmentStatus.ON_CHECKING,
        "score_old": None,
        "status_old": AssignmentStatus.NOT_SUBMITTED
    }

    sa.refresh_from_db()
    comment = create_personal_assignment_review(
        student_assignment=sa,
        is_draft=False,
        reviewer=teacher,
        message="",
        score_old=sa.score,
        status_old=sa.status,
        score_new=None,
        status_new=AssignmentStatus.COMPLETED,
        source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
    )
    assert comment.meta == {
        "score": None,
        "status": AssignmentStatus.COMPLETED,
        "score_old": Decimal('1'),
        "status_old": AssignmentStatus.ON_CHECKING
    }

    sa.refresh_from_db()
    comment = create_personal_assignment_review(
        student_assignment=sa,
        is_draft=False,
        reviewer=teacher,
        message="",
        score_old=sa.score,
        status_old=sa.status,
        score_new=Decimal('2'),
        status_new=sa.status,
        source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
    )
    assert comment.meta == {
        "score": Decimal('2'),
        "status": AssignmentStatus.COMPLETED,
        "score_old": None,
        "status_old": AssignmentStatus.COMPLETED
    }

    sa.refresh_from_db()
    comment = create_personal_assignment_review(
        student_assignment=sa,
        is_draft=False,
        reviewer=teacher,
        message="",
        score_old=sa.score,
        status_old=AssignmentStatus.COMPLETED,
        score_new=sa.score,
        status_new=AssignmentStatus.NEED_FIXES,
        source=AssignmentScoreUpdateSource.FORM_ASSIGNMENT
    )
    assert comment.meta == {
        "score": Decimal('2'),
        "status": AssignmentStatus.NEED_FIXES,
        "score_old": Decimal('2'),
        "status_old": AssignmentStatus.COMPLETED
    }


@pytest.mark.django_db
def test_create_assignment_solution_meta(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course,
                                  assignment__maximum_score=5)
    assert sa.status == AssignmentStatus.NOT_SUBMITTED
    solution = create_assignment_solution(personal_assignment=sa,
                                          created_by=sa.student,
                                          message="solution")
    assert sa.status == AssignmentStatus.ON_CHECKING
    assert solution.meta == {
        "score": None,
        "score_old": None,
        "status": AssignmentStatus.ON_CHECKING,
        "status_old": AssignmentStatus.NOT_SUBMITTED
    }
    sa.score = 5
    sa.status = AssignmentStatus.NEED_FIXES
    sa.save()
    solution = create_assignment_solution(personal_assignment=sa,
                                          created_by=sa.student,
                                          message="solution")
    assert solution.meta == {
        "score": sa.score,
        "score_old": sa.score,
        "status": AssignmentStatus.ON_CHECKING,
        "status_old": AssignmentStatus.NEED_FIXES
    }


StudentGroups = Tuple
Teachers = Set[int]


def create_buckets_testing_environment(group_sizes: List[int],
                                       buckets_structs: Dict[StudentGroups, Teachers]) -> Dict:
    course = CourseFactory()
    enrollments = EnrollmentFactory.create_batch(sum(group_sizes), course=course)
    teachers_primary_ids = set()
    for teachers in buckets_structs.values():
        teachers_primary_ids.update(teachers)
    teachers = CourseTeacherFactory.create_batch(len(teachers_primary_ids),
                                                 course=course)
    a = AssignmentFactory(course=course, assignee_mode=AssigneeMode.STUDENT_GROUP_BALANCED)
    student_groups = StudentGroupFactory.create_batch(len(group_sizes) - 1, course=course)
    if enrollments:
        student_groups.insert(0, enrollments[0].student_group)
    else:
        student_groups.insert(0, course.student_groups.first())
    transferred_cnt = group_sizes[0]
    for group_number in range(1, len(group_sizes)):
        group_size = group_sizes[group_number]
        to_move = enrollments[transferred_cnt:transferred_cnt + group_size]
        StudentGroupService.transfer_students(source=student_groups[0],
                                              destination=student_groups[group_number],
                                              enrollments=[enrollment.pk for enrollment in to_move])
        transferred_cnt += group_size
    buckets = []
    for bucket_sgs, bucket_teachers in buckets_structs.items():
        bucket = StudentGroupTeacherBucket.objects.create(assignment=a)
        bucket.groups.set(student_groups[i] for i in bucket_sgs)
        bucket.teachers.set(teachers[i] for i in bucket_teachers)
        bucket.save()
        buckets.append(bucket)
    result = {
        "course": course,
        "teachers": teachers,
        "student_groups": student_groups,
        "buckets": buckets
    }
    return result


@pytest.mark.django_db
def test_calculate_teachers_load_one_bucket_empty_group(client):
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[0],
        buckets_structs={
            (0,): {0},
        }
    ).values()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 0.0}


@pytest.mark.django_db
def test_calculate_teachers_load_operations(client):
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[0, 1, 4],
        buckets_structs={
            (0, 1, 2): {0},
        }
    ).values()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 5.}

    # Add teacher
    ct_extra = CourseTeacherFactory.create(course=course)
    buckets[0].teachers.add(ct_extra)
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 2.5, ct_extra.pk: 2.5}

    # Leave course
    sg3_e1 = student_groups[2].enrollments.first()
    sg3_e1.is_deleted = True
    sg3_e1.save()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 2., ct_extra.pk: 2.}

    # Solution submitted
    sg3_e4 = student_groups[2].enrollments.last()
    sg3_sa4 = sg3_e4.student.studentassignment_set.first()
    sg3_sa4.assignee = teachers[0]
    sg3_sa4.save()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 1.5, ct_extra.pk: 1.5}

    # Add student group
    sg4 = StudentGroupFactory.create(course=course)
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 1.5, ct_extra.pk: 1.5}

    # Add two students to student group
    sg4_e6, sg4_e7 = EnrollmentFactory.create_batch(2, course=course, student_group=sg4)
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 1.5, ct_extra.pk: 1.5}

    # Add student group to bucket
    bucket = StudentGroupTeacherBucket.objects.create(assignment=sg3_sa4.assignment)
    bucket.groups.add(sg4)
    bucket.teachers.add(ct_extra)
    bucket.save()
    buckets.append(bucket)
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 1.5, ct_extra.pk: 3.5}
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {ct_extra.pk: 3.5}

    # Submit from new student
    sg4_sa1 = sg4_e6.student.studentassignment_set.first()
    sg4_sa1.assignee = ct_extra
    sg4_sa1.save()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 1.5, ct_extra.pk: 2.5}
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {ct_extra.pk: 2.5}

    # Add teacher to new bucket
    bucket.teachers.add(teachers[0])
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 2., ct_extra.pk: 2.}
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {teachers[0].pk: 2., ct_extra.pk: 2.}

    # Teacher leave the course
    ct_extra.delete()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    # +1 because of assignee in submission from new student was ct_extra
    assert load == {teachers[0].pk: 5.}
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {teachers[0].pk: 5.}


@pytest.mark.django_db
def test_calculate_teachers_load_one_teacher_per_bucket(client):
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[0, 1, 2, 3],
        buckets_structs={
            (0,): {0},
            (1,): {1},
            (2,): {2},
            (3,): {3}
        }
    ).values()

    for index in range(len(buckets)):
        load = calculate_teachers_overall_expected_load_in_bucket(buckets[index])
        assert load == {teachers[index].pk: index}

    sg2_e1 = student_groups[1].enrollments.first()
    sg2_sa = sg2_e1.student.studentassignment_set.first()
    sg2_sa.assignee = teachers[1]
    sg2_sa.save()

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {teachers[1].pk: 0.}

    # Transfer student to another student group (and bucket)
    sg2_e1 = student_groups[2].enrollments.first()
    StudentGroupService.transfer_students(source=student_groups[2],
                                          destination=student_groups[0],
                                          enrollments=[sg2_e1.pk])
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 1.0}
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[2])
    assert load == {teachers[2].pk: 1.0}

    # Transferred student unenrolled
    sg2_e1.is_delete = True
    sg2_e1.save()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 0.0}

    # Teacher leave the course
    teachers[0].delete()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {}

    teachers[2].delete()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {}


@pytest.mark.django_db
def test_calculate_teachers_load_in_two_buckets(client):
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[1, 2, 3, 0],
        buckets_structs={
            (0, 1): {0},
            (2, 3): {0, 1, 2},
        }
    ).values()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 4.0}

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {
        teachers[0].pk: 4.0,
        teachers[1].pk: 1.0,
        teachers[2].pk: 1.0
    }

    sg1_enrollments = student_groups[0].enrollments.prefetch_related("student__studentassignment_set")
    sg1_sa = sg1_enrollments.first().student.studentassignment_set.first()
    sg1_sa.assignee = teachers[0]
    sg1_sa.save()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {teachers[0].pk: 3.0}

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {
        teachers[0].pk: 3.0,
        teachers[1].pk: 1.0,
        teachers[2].pk: 1.0
    }

    sg2_enrollments = student_groups[1].enrollments.prefetch_related("student__studentassignment_set")
    sg2_sa1 = sg2_enrollments.first().student.studentassignment_set.first()
    sg2_sa2 = sg2_enrollments.last().student.studentassignment_set.first()
    sg2_sa1.assignee = teachers[0]
    sg2_sa1.save()
    sg2_sa2.assignee = teachers[1]  # teacher from another bucket
    sg2_sa2.save()

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {
        teachers[0].pk: 1.0
    }

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {
        teachers[0].pk: 1.0,
        teachers[1].pk: 1.0,
        teachers[2].pk: 1.0
    }

    sg3_enrollments = student_groups[2].enrollments.prefetch_related("student__studentassignment_set")
    sg3_sa1, sg3_sa2, sg3_sa3 = [e.student.studentassignment_set.first() for e in sg3_enrollments.all()]
    sg3_sa1.assignee = teachers[0]
    sg3_sa1.save()
    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {
        teachers[0].pk: 2.0 / 3.0
    }

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {
        teachers[0].pk: 2.0 / 3.0,
        teachers[1].pk: 2.0 / 3.0,
        teachers[2].pk: 2.0 / 3.0
    }

    sg3_sa2.assignee = teachers[1]
    sg3_sa3.assignee = teachers[1]
    sg3_sa2.save()
    sg3_sa3.save()

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert load == {
        teachers[0].pk: 0.0
    }

    load = calculate_teachers_overall_expected_load_in_bucket(buckets[1])
    assert load == {
        teachers[0].pk: 0.0,
        teachers[1].pk: 0.0,
        teachers[2].pk: 0.0
    }


@pytest.mark.django_db
def test_calculate_teachers_load_all_teachers_per_bucket():
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[1, 1, 1, 1, 1, 1],
        buckets_structs={
            (0, 1): {0, 1, 2},
            (2, 3): {0, 1, 2},
            (4, 5): {0, 1, 2}
        }
    ).values()

    TWO = sum(1. / 3 for _ in range(6))
    exp_load = {teachers[0].pk: TWO, teachers[1].pk: TWO, teachers[2].pk: TWO}
    for i in range(len(buckets)):
        act_load = calculate_teachers_overall_expected_load_in_bucket(buckets[i])
        assert exp_load == act_load

    sg1_e = student_groups[0].enrollments.first()
    sg1_sa = sg1_e.student.studentassignment_set.first()
    sg1_sa.assignee = teachers[0]
    sg1_sa.save()
    FIVE_THIRDS = sum(1. / 3 for _ in range(5))
    exp_load = {teachers[0].pk: FIVE_THIRDS, teachers[1].pk: FIVE_THIRDS, teachers[2].pk: FIVE_THIRDS}
    for i in range(len(buckets)):
        act_load = calculate_teachers_overall_expected_load_in_bucket(buckets[i])
        assert exp_load == act_load

    buckets[0].teachers.remove(teachers[0])
    ELEVEN_SIXTH = 1. / 2 + 1. / 3 + 1. / 3 + 1. / 3 + 1. / 3
    exp_load = {teachers[1].pk: ELEVEN_SIXTH, teachers[2].pk: ELEVEN_SIXTH}
    act_load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert exp_load == act_load
    exp_load[teachers[0].pk] = 2. / 3 + 2. / 3
    for i in range(1, len(buckets)):
        act_load = calculate_teachers_overall_expected_load_in_bucket(buckets[i])
        assert exp_load == act_load


@pytest.mark.django_db
def test_calculate_teachers_load_assignments_load_independency():
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[1, 1, 1, 1, 1, 1],
        buckets_structs={
            (0, 1): {0, 1, 2},
            (2, 3): {0, 1, 2},
            (4, 5): {0, 1, 2}
        }
    ).values()

    exp_load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    a = AssignmentFactory(course=course, assignee_mode=AssigneeMode.STUDENT_GROUP_BALANCED)
    bucket = StudentGroupTeacherBucket.objects.create(assignment=a)
    bucket.groups.set(student_groups[:2])
    bucket.teachers.set([teachers[0]])
    bucket.save()
    act_load = calculate_teachers_overall_expected_load_in_bucket(buckets[0])
    assert exp_load == act_load

    act_load = calculate_teachers_overall_expected_load_in_bucket(bucket)
    assert {teachers[0].pk: 2.0} == act_load


@pytest.mark.django_db
def test_get_assignee_with_minimal_load_one_bucket():
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[0, 1, 2, 3],  # One group not in any of buckets
        buckets_structs={
            (0, 1, 2): {0, 1}
        }
    ).values()

    sg2_sa = student_groups[1].enrollments.first().student.studentassignment_set.first()
    assignee_one = get_assignee_with_minimal_load(sg2_sa)[0]
    sg2_sa.assignee = assignee_one
    sg2_sa.save()

    assignee_two = get_assignee_with_minimal_load(sg2_sa)[0]
    assert assignee_one != assignee_two

    sg3_enrollments = student_groups[2].enrollments.prefetch_related("student__studentassignment_set")
    sg3_sa1, sg3_sa2 = [e.student.studentassignment_set.first() for e in sg3_enrollments]

    assignee = get_assignee_with_minimal_load(sg3_sa1)[0]
    assert assignee == assignee_two
    sg3_sa1.assignee = assignee
    sg3_sa1.save()

    assignee = get_assignee_with_minimal_load(sg3_sa2)[0]
    assert assignee == assignee_one
    sg3_sa2.assignee = assignee
    sg3_sa2.save()

    sg4_enrollments = student_groups[3].enrollments.prefetch_related("student__studentassignment_set")
    sg4_sa = sg4_enrollments.first().student.studentassignment_set.first()
    assignee_list = get_assignee_with_minimal_load(sg4_sa)
    assert not assignee_list


@pytest.mark.django_db
def test_get_assignee_with_minimal_load_several_buckets():
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[2, 2, 2, 2, 2, 2, 3],  # One group not in any of buckets
        buckets_structs={
            (0, 1): {0, 1},
            (2, 3): {0, 2},
            (4, 5): {3, 4},
            (6,): {}
        }
    ).values()

    sg2_sa = student_groups[1].enrollments.first().student.studentassignment_set.first()
    assignee = get_assignee_with_minimal_load(sg2_sa)[0]
    # Because this teacher have more load in another buckets
    assert assignee == teachers[1]

    sg3_enrollments = student_groups[2].enrollments.prefetch_related("student__studentassignment_set")
    sg3_sa1, sg3_sa2 = [e.student.studentassignment_set.first() for e in sg3_enrollments]
    assignee = get_assignee_with_minimal_load(sg3_sa1)[0]
    # Same reason
    assert assignee == teachers[2]

    # Add more actual load on teacher[1]
    # Now load is ct0=4, ct1=2
    sg7_enrollments = student_groups[6].enrollments.prefetch_related("student__studentassignment_set")
    sg7_sa1, sg7_sa2, sg7_sa3 = [e.student.studentassignment_set.first() for e in sg7_enrollments]
    sg7_sa1.assignee = teachers[1]
    sg7_sa1.save()
    sg7_sa2.assignee = teachers[1]
    sg7_sa2.save()

    assignee = get_assignee_with_minimal_load(sg2_sa)[0]
    # Due to actual workload, teacher[0] has become preferred.
    assert assignee == teachers[0]

    # But only in first bucket, in the second situation has no changes.
    # Load: ct0=4, ct2=2
    assignee = get_assignee_with_minimal_load(sg3_sa1)[0]
    assert assignee == teachers[2]

    # Let's balance the load: add more to ct2
    sg1_enrollments = student_groups[0].enrollments.prefetch_related("student__studentassignment_set")
    sg1_sa1, sg1_sa2 = [e.student.studentassignment_set.first() for e in sg1_enrollments]
    sg1_sa1.assignee = teachers[2]
    sg1_sa2.assignee = teachers[2]
    sg1_sa1.save()
    sg1_sa2.save()
    assignee = get_assignee_with_minimal_load(sg3_sa1)[0]
    # Now teachers[0] more preferable
    assert assignee == teachers[0]

    # Make imbalanced again
    sg3_sa1.assignee = teachers[0]
    sg7_sa3.assignee = teachers[0]
    sg3_sa1.save()
    sg7_sa3.save()
    assignee = get_assignee_with_minimal_load(sg3_sa2)[0]
    assert assignee == teachers[2]

    sg5_enrollments = student_groups[4].enrollments.prefetch_related("student__studentassignment_set")
    sg5_sa1, sg5_sa2 = [e.student.studentassignment_set.first() for e in sg5_enrollments]
    assignee = get_assignee_with_minimal_load(sg5_sa1)[0]
    assert assignee == teachers[3]
    sg5_sa1.assignee = teachers[3]
    sg5_sa1.save()

    assignee = get_assignee_with_minimal_load(sg5_sa2)[0]
    assert assignee == teachers[4]

    assignee_list = get_assignee_with_minimal_load(sg7_sa1)
    assert not assignee_list


@pytest.mark.django_db
def test_get_assignee_with_minial_load_assignment_load_independency():
    course, teachers, student_groups, buckets = create_buckets_testing_environment(
        group_sizes=[1, 1],
        buckets_structs={
            (0,): {0, 1},
            (1,): {0, 1},
        }
    ).values()

    a = AssignmentFactory(course=course, assignee_mode=AssigneeMode.STUDENT_GROUP_BALANCED)
    bucket = StudentGroupTeacherBucket.objects.create(assignment=a)
    bucket.groups.set(student_groups)
    bucket.teachers.set(teachers)
    bucket.save()

    sg1_a1_sa = (student_groups[0].enrollments.first()
                 .student.studentassignment_set.filter(assignment__course=course)
                 .first())
    assignee_a1_sa1 = get_assignee_with_minimal_load(sg1_a1_sa)[0]
    assert assignee_a1_sa1 == teachers[0]

    # Assignments independency
    sg1_a2_sa = (student_groups[0].enrollments.first()
                 .student.studentassignment_set.filter(assignment=a)
                 .first())
    sg1_a2_sa.assignee = teachers[0]
    sg1_a2_sa.save()
    # Nothing changed for assignment1
    assignee_a1_sa1 = get_assignee_with_minimal_load(sg1_a1_sa)[0]
    assert assignee_a1_sa1 == teachers[0]
    # But changes in assignment2
    assignee_a2_sa1 = get_assignee_with_minimal_load(sg1_a2_sa)[0]
    assert assignee_a2_sa1 == teachers[1]

    # Add actual load on dependent teacher-bucket
    sg2_a1_sa = (student_groups[1].enrollments.first()
                 .student.studentassignment_set.filter(assignment__course=course)
                 .first())
    sg2_a1_sa.assignee = teachers[1]
    sg2_a1_sa.save()
    assignee_a1_sa1 = get_assignee_with_minimal_load(sg1_a1_sa)[0]
    assert assignee_a1_sa1 == teachers[0]

    # Independency check in both directions
    assignee_a2_sa1 = get_assignee_with_minimal_load(sg1_a2_sa)[0]
    assert assignee_a2_sa1 == teachers[1]
