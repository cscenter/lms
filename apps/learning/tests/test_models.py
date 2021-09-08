import datetime
import re
from datetime import timedelta
from decimal import Decimal

import pytest
import pytz

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.encoding import smart_str

from core.tests.factories import BranchFactory, LocationFactory, SiteFactory
from courses.constants import AssignmentFormat, SemesterTypes
from courses.models import CourseGroupModes, CourseNews, Semester
from courses.tests.factories import (
    AssignmentFactory, CourseClassAttachmentFactory, CourseClassFactory, CourseFactory,
    CourseNewsFactory, CourseTeacherFactory, LearningSpaceFactory, MetaCourseFactory,
    SemesterFactory
)
from learning.models import (
    AssignmentComment, AssignmentNotification, AssignmentSubmissionTypes,
    EnrollmentPeriod, StudentAssignment
)
from learning.settings import Branches
from learning.tests.factories import (
    AssignmentCommentFactory, AssignmentNotificationFactory,
    CourseNewsNotificationFactory, EnrollmentFactory, EnrollmentPeriodFactory,
    StudentAssignmentFactory, StudentGroupAssigneeFactory, StudentGroupFactory
)
from users.tests.factories import StudentFactory, TeacherFactory


@pytest.mark.django_db
def test_models__str__(mocker):
    mocked = mocker.patch("courses.tasks.maybe_upload_slides_yandex.delay")
    meta_course = MetaCourseFactory.build()
    assert smart_str(meta_course) == meta_course.name
    semester = Semester(year=2015, type='spring')
    assert smart_str(semester.year) in semester.name
    assert 'spring' in semester.name
    course = CourseFactory.create()
    assert smart_str(course.meta_course) in str(course)
    assert smart_str(course.semester) in str(course)
    course_news: CourseNews = CourseNewsFactory.create()
    assert smart_str(course_news.title) in str(course_news)
    assert smart_str(course_news.course) in str(course_news)
    course_class = CourseClassFactory()
    assert course_class.name in str(course_class)
    cca = (CourseClassAttachmentFactory.create(material__filename="foobar.pdf"))
    assert "foobar" in str(cca)
    assert "pdf" in str(cca)
    assignment = AssignmentFactory()
    assert assignment.title in str(assignment)
    assert smart_str(assignment.course) in str(assignment)
    student_assignment = StudentAssignmentFactory()
    assert smart_str(student_assignment.student.get_full_name()) in smart_str(student_assignment)
    assert smart_str(student_assignment.assignment) in str(student_assignment)
    assignment_comment = AssignmentCommentFactory()
    assert smart_str(assignment_comment.student_assignment.assignment) in str(assignment_comment)
    assert smart_str(assignment_comment.student_assignment
                     .student.get_full_name()) in str(assignment_comment)
    enrollment = EnrollmentFactory()
    assert smart_str(enrollment.course) in str(enrollment)
    assert smart_str(enrollment.student.get_full_name()) in str(enrollment)
    an = AssignmentNotificationFactory.create()
    assert smart_str(an.user.get_full_name()) in str(an)
    assert smart_str(an.student_assignment) in str(an)
    conn = CourseNewsNotificationFactory.create()
    assert smart_str(conn.user.get_full_name()) in str(conn)
    assert smart_str(conn.course_offering_news) in str(conn)


@pytest.mark.django_db
def test_student_assignment_submission_is_sent():
    u_student = StudentFactory()
    u_teacher = TeacherFactory()
    as_ = StudentAssignmentFactory(
        student=u_student,
        assignment__course__teachers=[u_teacher],
        assignment__submission_type=AssignmentFormat.ONLINE)
    # teacher comments first
    assert not as_.submission_is_received
    AssignmentCommentFactory.create(student_assignment=as_,
                                    author=u_teacher)
    as_.refresh_from_db()
    assert not as_.submission_is_received
    AssignmentCommentFactory.create(student_assignment=as_,
                                    author=u_student)
    as_.refresh_from_db()
    assert as_.submission_is_received
    # student comments first
    as_ = StudentAssignmentFactory(
        student=u_student,
        assignment__course__teachers=[u_teacher],
        assignment__submission_type=AssignmentFormat.ONLINE)
    as_.refresh_from_db()
    assert not as_.submission_is_received
    AssignmentCommentFactory.create(student_assignment=as_,
                                    author=u_student)
    as_.refresh_from_db()
    assert as_.submission_is_received
    AssignmentCommentFactory.create(student_assignment=as_,
                                    author=u_student)
    as_.refresh_from_db()
    assert as_.submission_is_received
    # assignment is offline
    as_ = StudentAssignmentFactory(
        student=u_student,
        assignment__course__teachers=[u_teacher],
        assignment__submission_type=AssignmentFormat.NO_SUBMIT)
    as_.refresh_from_db()
    assert not as_.submission_is_received
    AssignmentCommentFactory.create(student_assignment=as_,
                                    author=u_student)
    as_.refresh_from_db()
    assert not as_.submission_is_received


@pytest.mark.django_db
def test_student_assignment_state():
    import datetime

    from django.utils import timezone
    student = StudentFactory()
    a_online = AssignmentFactory.create(
        passing_score=5, maximum_score=10,
        submission_type=AssignmentFormat.ONLINE,
        deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
    )
    ctx = {'student': student, 'assignment': a_online}
    sa = StudentAssignment(score=0, **ctx)
    assert sa.state.value == sa.States.UNSATISFACTORY
    sa = StudentAssignment(score=4, **ctx)
    assert sa.state.value == sa.States.UNSATISFACTORY
    sa = StudentAssignment(score=5, **ctx)
    assert sa.state.value == sa.States.CREDIT
    sa = StudentAssignment(score=8, **ctx)
    assert sa.state.value == sa.States.GOOD
    sa = StudentAssignment(score=10, **ctx)
    assert sa.state.value == sa.States.EXCELLENT
    sa = StudentAssignment(**ctx)
    assert sa.state.value == sa.States.NOT_SUBMITTED
    a_offline = AssignmentFactory.create(
        passing_score=5, maximum_score=10,
        submission_type=AssignmentFormat.NO_SUBMIT,
        deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
    )
    ctx['assignment'] = a_offline
    sa = StudentAssignment(**ctx)
    assert sa.state.value == sa.States.NOT_CHECKED


@pytest.mark.django_db
def test_student_assignment_state_display():
    sa = StudentAssignmentFactory(score=30, assignment__maximum_score=50)
    assert smart_str(sa.assignment.maximum_score) in sa.state_display
    assert smart_str(sa.score) in sa.state_display
    sa = StudentAssignmentFactory(assignment__maximum_score=50)
    assert sa.state_display == StudentAssignment.States.labels.NOT_SUBMITTED


@pytest.mark.django_db
def test_student_assignment_state_short():
    sa = StudentAssignmentFactory(score=30, assignment__maximum_score=50)
    assert smart_str(sa.assignment.maximum_score) in sa.state_short
    assert smart_str(sa.score) in sa.state_short
    sa = StudentAssignmentFactory(assignment__maximum_score=50)
    state = StudentAssignment.States.get_choice(StudentAssignment.States.NOT_SUBMITTED)
    assert state.abbr in sa.state_short


@pytest.mark.django_db
def test_assignment_comment_attached_file():
    assignment_comment = AssignmentCommentFactory.create(attached_file__filename="foobar.pdf")
    file_name = assignment_comment.attached_file.name
    assert smart_str(assignment_comment.student_assignment.assignment.pk) in file_name
    assert smart_str(assignment_comment.student_assignment.student.pk) in file_name
    assert re.compile(r"/foobar(_[0-9a-zA-Z]+)?.pdf$").search(file_name)
    assert re.compile(r"^foobar(_[0-9a-zA-Z]+)?.pdf$").search(assignment_comment.attached_file_name)


@pytest.mark.django_db
def test_assignment_notification_validate():
    an = AssignmentNotificationFactory.create(
        user=StudentFactory(),
        is_about_passed=True)
    with pytest.raises(ValidationError):
        an.clean()


@pytest.mark.django_db
def test_enrollment_period(mocker, settings):
    year = 2016
    term_type = SemesterTypes.AUTUMN
    # Fix year and term
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    now_fixed = datetime.datetime(year, month=9, day=8, tzinfo=pytz.UTC)
    mocked_timezone.return_value = now_fixed
    # Default start is the beginning of the term
    term = SemesterFactory(year=year, type=term_type)
    enrollment_period = EnrollmentPeriodFactory(semester=term)
    term_start_dt = term.starts_at
    assert enrollment_period.starts_on == term_start_dt.date()
    # Start/End of the enrollment period always non-empty value, even
    # without calling .clean() method
    assert enrollment_period.ends_on is not None
    EnrollmentPeriod.objects.all().delete()
    # When we have only one day to enroll in the course
    site = SiteFactory(pk=settings.SITE_ID)
    enrollment_period = EnrollmentPeriod(semester=term,
                                         site=site,
                                         starts_on=term_start_dt.date(),
                                         ends_on=term_start_dt.date())
    enrollment_period.clean()
    enrollment_period.save()
    EnrollmentPeriod.objects.all().delete()
    # Values didn't overridden
    assert enrollment_period.starts_on == term_start_dt.date()
    assert enrollment_period.ends_on == term_start_dt.date()
    # Validation error: end > start
    with pytest.raises(ValidationError) as e:
        end_at = term_start_dt.date() - datetime.timedelta(days=1)
        ep = EnrollmentPeriod(semester=term,
                              site=site,
                              starts_on=term_start_dt.date(),
                              ends_on=end_at)
        ep.clean()
    # Empty start, none-empty end, but value < than `expected` start
    # enrollment period
    with pytest.raises(ValidationError) as e:
        end_at = term_start_dt.date() - datetime.timedelta(days=1)
        ep = EnrollmentPeriod(semester=term,
                              site=site,
                              ends_on=end_at)
        ep.clean()
    # Start should be inside semester
    with pytest.raises(ValidationError) as e:
        before_term_start = term_start_dt - datetime.timedelta(days=2)
        ep = EnrollmentPeriod(semester=term,
                              site=site,
                              starts_on=before_term_start.date())
        ep.clean()


@pytest.mark.django_db
def test_course_enrollment_is_open(settings, mocker):
    settings.ENROLLMENT_DURATION = 45
    year = 2016
    term_type = SemesterTypes.AUTUMN
    # timezone.now() should return some date from autumn 2016
    # but less than settings.ENROLLMENT_DURATION
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    now_fixed = datetime.datetime(year, month=9, day=8, tzinfo=pytz.UTC)
    mocked_timezone.return_value = now_fixed
    term = SemesterFactory.create_current()
    assert term.type == term_type
    assert term.year == year
    main_branch = BranchFactory(code=Branches.SPB,
                                site=SiteFactory(pk=settings.SITE_ID))
    co_spb = CourseFactory(semester=term, main_branch=main_branch)
    # We are inside enrollment period right now
    assert co_spb.enrollment_is_open
    # `completed_at` has more priority than term settings
    default_completed_at = co_spb.completed_at
    co_spb.completed_at = now_fixed.date()
    co_spb.save()
    assert co_spb.is_completed
    assert not co_spb.enrollment_is_open
    co_spb.completed_at = default_completed_at
    co_spb.save()
    # Test boundaries
    assert co_spb.enrollment_is_open
    ep = EnrollmentPeriod.objects.get(site_id=settings.SITE_ID, semester=term)
    ep.ends_on = now_fixed.date()
    ep.save()
    assert co_spb.enrollment_is_open
    ep.ends_on = now_fixed.date() - datetime.timedelta(days=1)
    ep.save()
    co_spb.refresh_from_db()
    assert not co_spb.enrollment_is_open
    ep.starts_on = now_fixed.date()
    ep.ends_on = now_fixed.date() + datetime.timedelta(days=1)
    ep.save()
    co_spb.refresh_from_db()
    assert co_spb.enrollment_is_open


@pytest.mark.django_db
def test_score_field():
    sa = StudentAssignmentFactory(assignment__maximum_score=50)
    sa.score = 20
    sa.save()
    sa.refresh_from_db()
    assert sa.score == Decimal('20')
    assert str(sa.score) == '20'
    sa.score = 10.00
    sa.save()
    sa.refresh_from_db()
    assert str(sa.score) == '10'
    sa.score = 20.50
    sa.save()
    sa.refresh_from_db()
    assert str(sa.score) == '20.5'


@pytest.mark.django_db
def test_soft_delete_student_assignment():
    assignment = AssignmentFactory()
    sa = StudentAssignmentFactory(assignment=assignment)
    comment = AssignmentCommentFactory(student_assignment=sa)
    assert AssignmentNotification.objects.count() == 1
    assert AssignmentComment.objects.count() == 1
    sa.delete()
    assert sa.is_deleted
    assert StudentAssignment.objects.count() == 0
    assert StudentAssignment.trash.count() == 1
    assert assignment.studentassignment_set.count() == 0
    assert assignment.studentassignment_set(manager='trash').count() == 1
    assert AssignmentNotification.objects.count() == 1
    assert AssignmentComment.objects.count() == 0
    assert AssignmentComment.trash.count() == 1
    assert sa.assignmentcomment_set.count() == 0
    # Restore
    sa.restore()
    assert not sa.is_deleted
    assert AssignmentComment.objects.count() == 1


@pytest.mark.django_db
def test_learning_space_full_name():
    location = LocationFactory(name='Zombie', address='ZombieLand')
    learning_space = LearningSpaceFactory(location=location, name='')
    assert learning_space.full_name == location.name
    learning_space = LearningSpaceFactory(location=location, name='Hello')
    assert learning_space.full_name == 'Hello, Zombie'


@pytest.mark.django_db
def test_student_assignment_execution_time():
    student_assignment = StudentAssignmentFactory()
    solution1 = AssignmentCommentFactory(student_assignment=student_assignment,
                                         type=AssignmentSubmissionTypes.SOLUTION,
                                         execution_time=timedelta(hours=2))
    solution2 = AssignmentCommentFactory(student_assignment=student_assignment,
                                         type=AssignmentSubmissionTypes.SOLUTION,
                                         execution_time=timedelta(minutes=3))
    # Doesn't take into account even if an exec time has been provided
    comment1 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        type=AssignmentSubmissionTypes.COMMENT,
                                        execution_time=timedelta(hours=2))
    # student_assignment.compute_fields("execution_time")
    assert student_assignment.execution_time == timedelta(hours=2, minutes=3)
    # Recalculate on removing solution through admin interface
    solution2.delete()
    assert student_assignment.execution_time == timedelta(hours=2)


@pytest.mark.django_db
def test_student_group_assignee_model_constraint_unique_teacher_per_student_group():
    course = CourseFactory(group_mode=CourseGroupModes.MANUAL)
    course_teacher1, course_teacher2 = CourseTeacherFactory.create_batch(2, course=course)
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)

    StudentGroupAssigneeFactory(student_group=student_group1, assignee=course_teacher1)
    StudentGroupAssigneeFactory(student_group=student_group1, assignee=course_teacher2)
    StudentGroupAssigneeFactory(student_group=student_group2, assignee=course_teacher1)
    # Create savepoint here or subsequent calls to db after IntegrityError will
    # fail with TransactionManagementError
    with transaction.atomic():
        with pytest.raises(IntegrityError) as e:
            StudentGroupAssigneeFactory(student_group=student_group1,
                                        assignee=course_teacher1)


@pytest.mark.django_db
def test_student_group_assignee_constraint_unique_teacher_per_student_group_per_assignment():
    course = CourseFactory(group_mode=CourseGroupModes.MANUAL)
    course_teacher1, course_teacher2 = CourseTeacherFactory.create_batch(2, course=course)
    assignment = AssignmentFactory(course=course)
    student_group = StudentGroupFactory(course=course)

    StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher1)
    # Create savepoint here or subsequent calls to db after IntegrityError will
    # fail with TransactionManagementError
    with transaction.atomic():
        with pytest.raises(IntegrityError) as e:
            StudentGroupAssigneeFactory(student_group=student_group,
                                        assignee=course_teacher1)
    StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher2,
                                assignment=assignment)
    # Make sure course teacher assigned on course level
    # could be "overridden" on assignment level
    StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher1,
                                assignment=assignment)
    # Make sure we can't add course teacher on assignment level more than once
    with transaction.atomic():
        with pytest.raises(IntegrityError) as e:
            StudentGroupAssigneeFactory(student_group=student_group, assignee=course_teacher1,
                                        assignment=assignment)
