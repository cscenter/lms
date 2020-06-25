# -*- coding: utf-8 -*-

import datetime
from decimal import Decimal
from unittest import mock

import pytest
import pytz
from django.core.exceptions import ValidationError

from core.tests.factories import SiteFactory, BranchFactory
from core.tests.utils import CSCTestCase
from django.utils.encoding import smart_text

from learning.settings import Branches
from learning.tests.factories import StudentAssignmentFactory, \
    AssignmentCommentFactory, \
    EnrollmentFactory, AssignmentNotificationFactory, \
    CourseNewsNotificationFactory, EnrollmentPeriodFactory
from courses.tests.factories import MetaCourseFactory, SemesterFactory, CourseFactory, \
    CourseNewsFactory, CourseClassFactory, CourseClassAttachmentFactory, \
    AssignmentFactory
from learning.models import StudentAssignment, AssignmentNotification, \
    AssignmentComment, EnrollmentPeriod
from courses.models import Semester, CourseNews, CourseReview, \
    AssignmentSubmissionTypes
from courses.constants import SemesterTypes
from courses.utils import get_term_starts_at
from users.tests.factories import UserFactory, StudentFactory, \
    TeacherFactory


class CommonTests(CSCTestCase):
    @mock.patch("courses.tasks.maybe_upload_slides_yandex.delay")
    def test_to_strings(self, _):
        meta_course = MetaCourseFactory.build()
        self.assertEqual(smart_text(meta_course), meta_course.name)
        semester = Semester(year=2015, type='spring')
        self.assertIn(smart_text(semester.year), smart_text(semester))
        self.assertIn('spring', smart_text(semester))
        co = CourseFactory.create()
        self.assertIn(smart_text(co.meta_course), smart_text(co))
        self.assertIn(smart_text(co.semester), smart_text(co))
        con: CourseNews = CourseNewsFactory.create()
        self.assertIn(smart_text(con.title), smart_text(con))
        self.assertIn(smart_text(con.course), smart_text(con))
        cc = CourseClassFactory.create()
        self.assertIn(cc.name, smart_text(cc))
        cca = (CourseClassAttachmentFactory
               .create(material__filename="foobar.pdf"))
        self.assertIn("foobar", smart_text(cca))
        self.assertIn("pdf", smart_text(cca))
        a = AssignmentFactory.create()
        self.assertIn(a.title, smart_text(a))
        self.assertIn(smart_text(a.course), smart_text(a))
        as_ = StudentAssignmentFactory.create()
        self.assertIn(smart_text(as_.student.get_full_name()), smart_text(as_))
        self.assertIn(smart_text(as_.assignment), smart_text(as_))
        ac = AssignmentCommentFactory.create()
        self.assertIn(smart_text(ac.student_assignment.assignment),
                      smart_text(ac))
        self.assertIn(smart_text(ac.student_assignment
                                 .student.get_full_name()),
                      smart_text(ac))
        e = EnrollmentFactory.create()
        self.assertIn(smart_text(e.course), smart_text(e))
        self.assertIn(smart_text(e.student.get_full_name()), smart_text(e))
        an = AssignmentNotificationFactory.create()
        self.assertIn(smart_text(an.user.get_full_name()), smart_text(an))
        self.assertIn(smart_text(an.student_assignment), smart_text(an))
        conn = CourseNewsNotificationFactory.create()
        self.assertIn(smart_text(conn.user.get_full_name()), smart_text(conn))
        self.assertIn(smart_text(conn.course_offering_news), smart_text(conn))


class StudentAssignmentTests(CSCTestCase):
    def test_clean(self):
        u1 = StudentFactory()
        u2 = UserFactory.create(groups=[])
        as_ = StudentAssignmentFactory.create(student=u1)
        as_.student = u2
        self.assertRaises(ValidationError, as_.clean)
        as_.student = u1
        as_.save()
        as_.score = as_.assignment.maximum_score + 1
        self.assertRaises(ValidationError, as_.clean)
        as_.score = as_.assignment.maximum_score
        as_.save()

    def test_submission_is_sent(self):
        u_student = StudentFactory()
        u_teacher = TeacherFactory()
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course__teachers=[u_teacher],
            assignment__submission_type=AssignmentSubmissionTypes.ONLINE)
        # teacher comments first
        self.assertFalse(as_.submission_is_received)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_teacher)
        as_.refresh_from_db()
        self.assertFalse(as_.submission_is_received)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertTrue(as_.submission_is_received)
        # student comments first
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course__teachers=[u_teacher],
            assignment__submission_type=AssignmentSubmissionTypes.ONLINE)
        as_.refresh_from_db()
        self.assertFalse(as_.submission_is_received)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertTrue(as_.submission_is_received)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertTrue(as_.submission_is_received)
        # assignment is offline
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course__teachers=[u_teacher],
            assignment__submission_type=AssignmentSubmissionTypes.OTHER)
        as_.refresh_from_db()
        self.assertFalse(as_.submission_is_received)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertFalse(as_.submission_is_received)

    def test_student_assignment_state(self):
        import datetime
        from django.utils import timezone
        student = StudentFactory()
        a_online = AssignmentFactory.create(
            passing_score=5, maximum_score=10,
            submission_type=AssignmentSubmissionTypes.ONLINE,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx = {'student': student, 'assignment': a_online}
        a_s = StudentAssignment(score=0, **ctx)
        self.assertEqual(a_s.state.value, a_s.States.UNSATISFACTORY)
        a_s = StudentAssignment(score=4, **ctx)
        self.assertEqual(a_s.state.value, a_s.States.UNSATISFACTORY)
        a_s = StudentAssignment(score=5, **ctx)
        self.assertEqual(a_s.state.value, a_s.States.CREDIT)
        a_s = StudentAssignment(score=8, **ctx)
        self.assertEqual(a_s.state.value, a_s.States.GOOD)
        a_s = StudentAssignment(score=10, **ctx)
        self.assertEqual(a_s.state.value, a_s.States.EXCELLENT)
        a_s = StudentAssignment(**ctx)
        self.assertEqual(a_s.state.value, a_s.States.NOT_SUBMITTED)
        a_offline = AssignmentFactory.create(
            passing_score=5, maximum_score=10,
            submission_type=AssignmentSubmissionTypes.OTHER,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx['assignment'] = a_offline
        a_s = StudentAssignment(**ctx)
        self.assertEqual(a_s.state.value, a_s.States.NOT_CHECKED)

    def test_state_display(self):
        as_ = StudentAssignmentFactory(score=30,
                                       assignment__maximum_score=50)
        self.assertIn(smart_text(as_.assignment.maximum_score), as_.state_display)
        self.assertIn(smart_text(as_.score), as_.state_display)
        as_ = StudentAssignmentFactory(assignment__maximum_score=50)
        self.assertEqual(StudentAssignment.States.labels.NOT_SUBMITTED,
                         as_.state_display)

    def test_state_short(self):
        as_ = StudentAssignmentFactory(score=30,
                                       assignment__maximum_score=50)
        self.assertIn(smart_text(as_.assignment.maximum_score), as_.state_short)
        self.assertIn(smart_text(as_.score), as_.state_short)
        as_ = StudentAssignmentFactory(assignment__maximum_score=50)
        state = StudentAssignment.States.get_choice(StudentAssignment.States.NOT_SUBMITTED)
        self.assertEqual(state.abbr, as_.state_short)


class AssignmentCommentTests(CSCTestCase):
    def test_attached_file(self):
        ac = AssignmentCommentFactory.create(
            attached_file__filename="foobar.pdf")
        self.assertIn(smart_text(ac.student_assignment.assignment.pk),
                      ac.attached_file.name)
        self.assertIn(smart_text(ac.student_assignment.student.pk),
                      ac.attached_file.name)
        self.assertRegex(ac.attached_file.name, "/foobar(_[0-9a-zA-Z]+)?.pdf$")
        self.assertRegex(ac.attached_file_name, "^foobar(_[0-9a-zA-Z]+)?.pdf$")


class AssignmentNotificationTests(CSCTestCase):
    def test_clean(self):
        an = AssignmentNotificationFactory.create(
            user=StudentFactory(),
            is_about_passed=True)
        self.assertRaises(ValidationError, an.clean)


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
