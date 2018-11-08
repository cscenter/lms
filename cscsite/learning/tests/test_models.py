# -*- coding: utf-8 -*-

import datetime
import os
from decimal import Decimal
from unittest import mock

import pytest
import pytz
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.encoding import smart_text
from mock import patch

from learning.factories import MetaCourseFactory, CourseFactory, \
    CourseNewsFactory, CourseClassFactory, CourseClassAttachmentFactory, \
    AssignmentFactory, StudentAssignmentFactory, AssignmentCommentFactory, \
    EnrollmentFactory, AssignmentNotificationFactory, \
    CourseNewsNotificationFactory, AssignmentAttachmentFactory, \
    SemesterFactory
from learning.models import StudentAssignment
from courses.models import Course, Semester, CourseNews, Assignment
from learning.settings import AssignmentStates
from courses.settings import SemesterTypes
from learning.utils import get_term_start, next_term_starts_at
from users.factories import UserFactory, StudentCenterFactory, \
    TeacherCenterFactory


class CommonTests(TestCase):
    @mock.patch("learning.tasks.maybe_upload_slides_yandex.delay")
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


@pytest.mark.django_db
def test_semester_starts_ends():
    import datetime
    from django.utils import timezone
    spring_2015_date = (datetime.datetime(2015, 4, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    # Summer term starts from 1 jul
    summer_2015_date = (datetime.datetime(2015, 7, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    autumn_2015_date = (datetime.datetime(2015, 11, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    spring_2016_date = (datetime.datetime(2016, 4, 8, 0, 0, 0)
                        .replace(tzinfo=timezone.utc))
    spring_2015 = SemesterFactory(type='spring', year=2015)
    summer_2015 = SemesterFactory(type='summer', year=2015)
    autumn_2015 = SemesterFactory(type='autumn', year=2015)
    spring_2016 = SemesterFactory(type='spring', year=2016)
    # Check starts < ends
    assert spring_2015.starts_at < spring_2015.ends_at
    assert summer_2015.starts_at < summer_2015.ends_at
    assert autumn_2015.starts_at < autumn_2015.ends_at
    # Check relativity
    assert spring_2015.ends_at < summer_2015.starts_at
    assert summer_2015.ends_at < autumn_2015.starts_at
    assert autumn_2015.ends_at < spring_2016.starts_at
    # Spring date inside spring semester
    assert spring_2015.starts_at < spring_2015_date
    assert spring_2015_date < spring_2015.ends_at
    # And outside others
    assert spring_2015_date < summer_2015.starts_at
    assert spring_2016_date > autumn_2015.ends_at
    # Summer date inside summer term
    assert summer_2015_date > summer_2015.starts_at
    assert summer_2015_date < summer_2015.ends_at
    # Autumn date inside autumn term
    assert autumn_2015_date > autumn_2015.starts_at
    assert autumn_2015_date < autumn_2015.ends_at


def test_semester_cmp():
    from learning.utils import get_term_index
    index = get_term_index(2013, 'spring')
    s2013_spring = Semester(type='spring', year=2013, index=index)
    index = get_term_index(2013, 'autumn')
    s2013_autumn = Semester(type='autumn', year=2013, index=index)
    index = get_term_index(2013, 'summer')
    s2013_summer = Semester(type='summer', year=2013, index=index)
    index = get_term_index(2014, 'spring')
    s2014_spring = Semester(type='spring', year=2014, index=index)
    assert s2013_spring < s2013_autumn
    assert s2013_spring < s2013_summer
    assert s2013_summer < s2013_autumn
    assert s2013_summer < s2014_spring


class CourseTests(TestCase):
    def test_in_current_term(self):
        """
        In near future only one course should be "ongoing".
        """
        import datetime
        from django.utils import timezone
        future_year = datetime.datetime.now().year + 20
        some_year = future_year - 5
        semesters = [Semester(year=year,
                              type=t)
                     for t in ['spring', 'autumn']
                     for year in range(2010, future_year)]
        # Save semesters in db dut to django 1.8 not supported build strategy 
        # with SubFactory
        for semester in semesters:
            semester.save()
        old_now = timezone.now
        timezone.now = lambda: (datetime.datetime(some_year, 4, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        n_ongoing = sum((Course(meta_course=MetaCourseFactory(name="Test course"),
                                semester=semester)
                         .in_current_term)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = lambda: (datetime.datetime(some_year, 11, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        n_ongoing = sum((Course(meta_course=MetaCourseFactory(name="Test course"),
                                semester=semester)
                         .in_current_term)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = old_now

    def test_completed_at_default(self):
        semester = SemesterFactory(year=2017, type=SemesterTypes.AUTUMN)
        meta_course = MetaCourseFactory()
        co = CourseFactory.build(meta_course=meta_course,
                                 semester=semester)
        assert not co.completed_at
        co.save()
        next_term_dt = next_term_starts_at(semester.index, co.get_city_timezone())
        assert co.completed_at == next_term_dt.date()


@pytest.mark.django_db
def test_course_composite_fields():
    co = CourseFactory()
    assert not co.materials_files
    assert not co.materials_slides
    assert not co.materials_video
    cc = CourseClassFactory(course=co, video_url="https://link/to/youtube")
    co.refresh_from_db()
    assert not co.materials_files
    assert not co.materials_slides
    assert co.materials_video
    _ = CourseClassAttachmentFactory(course_class=cc)
    co.refresh_from_db()
    assert co.materials_files


class CourseClassTests(TestCase):
    def test_slides_file_name(self):
        slide_fname = "foobar.pdf"
        cc = CourseClassFactory.create()
        fname = cc._slides_file_name(slide_fname)
        co = cc.course
        self.assertIn(co.meta_course.slug.replace("-", "_"), fname)
        self.assertIn(co.semester.slug.replace("-", "_"), fname)
        _, ext = os.path.splitext(slide_fname)
        self.assertIn(ext, fname)

    def test_start_end_validation(self):
        time1 = "13:00"
        time2 = "14:20"
        cc = CourseClassFactory.create(starts_at=time1, ends_at=time2)
        self.assertEqual(None, cc.clean())
        cc = CourseClassFactory.create(starts_at=time2, ends_at=time1)
        self.assertRaises(ValidationError, cc.clean)

    def test_display_prop(self):
        cc = CourseClassFactory.create(type='lecture')
        self.assertEqual("Lecture", cc.get_type_display())

    # TODO: refactor with pytest tmp file, fuck this patching
    @patch('slides.slideshare.upload_slides')
    @patch('slides.yandex_disk.upload_slides')
    @pytest.mark.skip(msg="Upload logic moved to django-rq, should rewrite test")
    def test_slides_file_name(self, upload_to_slideshare, upload_to_yandex):
        slides_fname = "foobar.pdf"
        upload_to_slideshare.return_value = "slideshare_embed_code"
        upload_to_yandex.return_value = "yandex_return"
        cc = CourseClassFactory.create(slides__filename=slides_fname)
        self.assertIn("/", cc.slides.name)
        self.assertNotIn("/", cc.slides_file_name)
        self.assertTrue(upload_to_slideshare.called)
        self.assertTrue(upload_to_yandex.called)


class AssignmentTest(TestCase):
    def test_clean(self):
        co1 = CourseFactory.create()
        co2 = CourseFactory.create()
        a = AssignmentFactory.create(course=co1)
        a_copy = Assignment.objects.filter(pk=a.pk).get()
        a_copy.course = co2
        self.assertRaises(ValidationError, a_copy.clean)
        a_copy.course = co1
        a_copy.save()
        a_copy.passing_score = a.maximum_score + 1
        self.assertRaises(ValidationError, a_copy.clean)

    def test_is_open(self):
        import datetime
        from django.utils import timezone
        a = AssignmentFactory.create()
        self.assertTrue(a.is_open)
        a.deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                         - datetime.timedelta(days=1))
        self.assertFalse(a.is_open)


class AssignmentAttachmentTest(TestCase):
    def test_attached_file_name(self):
        fname = "foobar.pdf"
        aa = AssignmentAttachmentFactory.create(attachment__filename=fname)
        self.assertRegex(aa.file_name,
                                 "^foobar(_[0-9a-zA-Z]+)?.pdf$")


class StudentAssignmentTests(TestCase):
    def test_clean(self):
        u1 = StudentCenterFactory()
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
        u_student = StudentCenterFactory()
        u_teacher = TeacherCenterFactory()
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course__teachers=[u_teacher],
            assignment__is_online=True)
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
            assignment__is_online=True)
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
            assignment__is_online=False)
        as_.refresh_from_db()
        self.assertFalse(as_.submission_is_received)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertFalse(as_.submission_is_received)

    def test_student_assignment_state(self):
        import datetime
        from django.utils import timezone
        student = StudentCenterFactory()
        a_online = AssignmentFactory.create(
            passing_score=5, maximum_score=10, is_online=True,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx = {'student': student, 'assignment': a_online}
        a_s = StudentAssignment(score=0, **ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.UNSATISFACTORY)
        a_s = StudentAssignment(score=4, **ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.UNSATISFACTORY)
        a_s = StudentAssignment(score=5, **ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.CREDIT)
        a_s = StudentAssignment(score=8, **ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.GOOD)
        a_s = StudentAssignment(score=10, **ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.EXCELLENT)
        a_s = StudentAssignment(**ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.NOT_SUBMITTED)
        a_offline = AssignmentFactory.create(
            passing_score=5, maximum_score=10, is_online=False,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx['assignment'] = a_offline
        a_s = StudentAssignment(**ctx)
        self.assertEqual(a_s.state.value, AssignmentStates.NOT_CHECKED)

    def test_state_display(self):
        as_ = StudentAssignmentFactory(score=30,
                                       assignment__maximum_score=50)
        self.assertIn(smart_text(as_.assignment.maximum_score), as_.state_display)
        self.assertIn(smart_text(as_.score), as_.state_display)
        as_ = StudentAssignmentFactory(assignment__maximum_score=50)
        self.assertEqual(AssignmentStates.labels.NOT_SUBMITTED,
                         as_.state_display)

    def test_state_short(self):
        as_ = StudentAssignmentFactory(score=30,
                                       assignment__maximum_score=50)
        self.assertIn(smart_text(as_.assignment.maximum_score), as_.state_short)
        self.assertIn(smart_text(as_.score), as_.state_short)
        as_ = StudentAssignmentFactory(assignment__maximum_score=50)
        state = AssignmentStates.get_choice(AssignmentStates.NOT_SUBMITTED)
        self.assertEqual(state.abbr, as_.state_short)


class AssignmentCommentTests(TestCase):
    def test_attached_file(self):
        ac = AssignmentCommentFactory.create(
            attached_file__filename="foobar.pdf")
        self.assertIn(smart_text(ac.student_assignment.assignment.pk),
                      ac.attached_file.name)
        self.assertIn(smart_text(ac.student_assignment.student.pk),
                      ac.attached_file.name)
        self.assertRegex(ac.attached_file.name, "/foobar(_[0-9a-zA-Z]+)?.pdf$")
        self.assertRegex(ac.attached_file_name, "^foobar(_[0-9a-zA-Z]+)?.pdf$")


class EnrollmentTests(TestCase):
    def test_clean(self):
        e = EnrollmentFactory.create(student=UserFactory.create())
        self.assertRaises(ValidationError, e.clean)


class AssignmentNotificationTests(TestCase):
    def test_clean(self):
        an = AssignmentNotificationFactory.create(
            user=StudentCenterFactory(),
            is_about_passed=True)
        self.assertRaises(ValidationError, an.clean)


@pytest.mark.django_db
def test_semester_enrollment_period(mocker):
    year = 2016
    term_type = SemesterTypes.AUTUMN
    # Fix year and term
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    now_fixed = datetime.datetime(year, month=9, day=8, tzinfo=pytz.UTC)
    mocked_timezone.return_value = now_fixed
    # Default start is the beginning of the term
    term = SemesterFactory(year=year, type=term_type)
    term_start_dt = get_term_start(year, term_type, pytz.UTC)
    assert term.enrollment_start_at == term_start_dt.date()
    # Start/End of the enrollment period always non-empty value, even
    # without calling .clean() method
    assert term.enrollment_end_at is not None
    # When we have only one day to enroll in the course
    Semester.objects.all().delete()
    term = SemesterFactory.build(year=year, type=term_type,
                                 enrollment_start_at=term_start_dt.date(),
                                 enrollment_end_at=term_start_dt.date())
    try:
        term.clean()
        term.save()
    except ValidationError:
        pytest.fail("Enrollment period should be valid")
    # Values didn't overridden
    assert term.enrollment_start_at == term_start_dt.date()
    assert term.enrollment_end_at == term_start_dt.date()
    # End > Start
    Semester.objects.all().delete()
    with pytest.raises(ValidationError) as e:
        end_at = term_start_dt.date() - datetime.timedelta(days=1)
        term = SemesterFactory.build(year=year, type=term_type,
                                     enrollment_start_at=term_start_dt.date(),
                                     enrollment_end_at=end_at)
        term.clean()
    # Empty start, none-empty end, but value < than `expected` start
    # enrollment period
    Semester.objects.all().delete()
    with pytest.raises(ValidationError) as e:
        end_at = term_start_dt.date() - datetime.timedelta(days=1)
        term = SemesterFactory.build(year=year, type=term_type,
                                     enrollment_end_at=end_at)
        term.clean()
    # Do not validate that start/end inside term bounds
    Semester.objects.all().delete()
    start_at = term_start_dt.date() + datetime.timedelta(weeks=42)
    term = SemesterFactory.build(year=year, type=term_type,
                                 enrollment_start_at=start_at,
                                 enrollment_end_at=start_at)
    term.clean()


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
    term_start_dt = get_term_start(year, term_type, pytz.UTC)
    assert term.enrollment_start_at == term_start_dt.date()
    co_spb = CourseFactory.create(semester=term, city_id='spb',
                                  is_open=False)
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
    term.enrollment_end_at = now_fixed.date()
    term.save()
    assert co_spb.enrollment_is_open
    term.enrollment_end_at = now_fixed.date() - datetime.timedelta(days=1)
    term.save()
    co_spb.refresh_from_db()
    assert not co_spb.enrollment_is_open
    term.enrollment_start_at = now_fixed.date()
    term.enrollment_end_at = now_fixed.date() + datetime.timedelta(days=1)
    term.save()
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
def test_course_get_reviews(settings):
    meta_course1, meta_course2 = MetaCourseFactory.create_batch(2)
    CourseFactory(meta_course=meta_course1, city_id='spb',
                  semester__year=2015, reviews='aaa')
    CourseFactory(meta_course=meta_course2, city_id='spb',
                  semester__year=2015, reviews='zzz')
    co = CourseFactory(meta_course=meta_course1, city_id='spb',
                       semester__year=2016, reviews='bbb')
    CourseFactory(meta_course=meta_course1, city_id='nsk',
                  semester__year=2016, reviews='ccc')
    assert len(co.get_reviews()) == 2
