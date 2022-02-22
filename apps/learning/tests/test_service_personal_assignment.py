from decimal import Decimal

import pytest
from future.backports.datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

from courses.constants import AssigneeMode, AssignmentFormat, AssignmentStatus
from courses.models import CourseGroupModes, CourseTeacher
from courses.tests.factories import AssignmentFactory, CourseFactory
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment,
    PersonalAssignmentActivity, StudentAssignment
)
from learning.services import EnrollmentService
from learning.services.personal_assignment_service import (
    create_assignment_comment, create_assignment_solution,
    create_personal_assignment_review, resolve_assignees_for_personal_assignment,
    update_personal_assignment_score, update_personal_assignment_stats,
    update_personal_assignment_status
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
def test_service_update_personal_assignment_stats_published():
    curator = CuratorFactory()
    student_assignment = StudentAssignmentFactory()
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
    assert solutions_stats['first'] == comment1.created.replace(microsecond=0)
    assert 'last' in solutions_stats
    assert solutions_stats['last'] == fixed_dt.replace(microsecond=0)


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
def test_update_personal_assignment_status():
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
    AssignmentCommentFactory(student_assignment=sa,
                             type=AssignmentSubmissionTypes.SOLUTION)
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
def test_create_personal_assignment_review():
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
                                          status_new=sa.status
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
                                                status_new=sa.status
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
                                                status_new=sa.status
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
                                                status_new=AssignmentStatus.NEED_FIXES
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
                                                status_new=sa.status
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
                                              status_new=AssignmentStatus.COMPLETED
                                              )
    sa.refresh_from_db()  # atomic doesn't restore state
    assert exc_info.value.code == 'score_overflow'
    assert sa.score != 6
    assert sa.status != AssignmentStatus.COMPLETED
    assert AssignmentComment.objects.count() == 0

    # Provided forbidden status
    create_assignment_solution(personal_assignment=sa,
                               created_by=sa.student,
                               message="solution")
    sa.refresh_from_db()  # above method changes StudentAssignment
    with pytest.raises(ValidationError) as exc_info:
        with transaction.atomic():
            create_personal_assignment_review(student_assignment=sa,
                                              reviewer=teacher,
                                              is_draft=False,
                                              message="Some text",
                                              score_old=sa.score,
                                              score_new=Decimal('5'),
                                              status_old=sa.status,
                                              status_new=AssignmentStatus.NOT_SUBMITTED
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
                                              status_new=AssignmentStatus.NEED_FIXES
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
                                              status_new=AssignmentStatus.NEED_FIXES
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
                                              status_new=AssignmentStatus.NEED_FIXES
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
                                              status_new=AssignmentStatus.NEED_FIXES
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
        status_new=AssignmentStatus.ON_CHECKING
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
        status_new=AssignmentStatus.COMPLETED
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
        status_new=sa.status
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
        status_new=AssignmentStatus.NEED_FIXES
    )
    assert comment.meta == {
        "score": Decimal('2'),
        "status": AssignmentStatus.NEED_FIXES,
        "score_old": Decimal('2'),
        "status_old": AssignmentStatus.COMPLETED
    }
