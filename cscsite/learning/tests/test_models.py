# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
import datetime

import unittest

import pytest
from django.utils.timezone import now
from mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.encoding import smart_text

from learning.factories import CourseFactory, CourseOfferingFactory, \
    CourseOfferingNewsFactory, CourseClassFactory, CourseClassAttachmentFactory, \
    AssignmentFactory, StudentAssignmentFactory, AssignmentCommentFactory, \
    EnrollmentFactory, AssignmentNotificationFactory, \
    CourseOfferingNewsNotificationFactory, AssignmentAttachmentFactory, \
    SemesterFactory
from learning.models import Semester, CourseOffering, CourseClass, Assignment, \
    StudentAssignment
from learning.settings import SEMESTER_TYPES
from users.factories import UserFactory, StudentCenterFactory, \
    TeacherCenterFactory


class CommonTests(TestCase):
    def test_to_strings(self):
        course = CourseFactory.build()
        self.assertEquals(smart_text(course), course.name)
        semester = Semester(year=2015, type='spring')
        self.assertIn(smart_text(semester.year), smart_text(semester))
        self.assertIn('spring', smart_text(semester))
        co = CourseOfferingFactory.create()
        self.assertIn(smart_text(co.course), smart_text(co))
        self.assertIn(smart_text(co.semester), smart_text(co))
        con = CourseOfferingNewsFactory.create()
        self.assertIn(smart_text(con.title), smart_text(con))
        self.assertIn(smart_text(con.course_offering), smart_text(con))
        cc = CourseClassFactory.create()
        self.assertIn(cc.name, smart_text(cc))
        cca = (CourseClassAttachmentFactory
               .create(material__filename="foobar.pdf"))
        self.assertIn("foobar", smart_text(cca))
        self.assertIn("pdf", smart_text(cca))
        a = AssignmentFactory.create()
        self.assertIn(a.title, smart_text(a))
        self.assertIn(smart_text(a.course_offering), smart_text(a))
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
        self.assertIn(smart_text(e.course_offering), smart_text(e))
        self.assertIn(smart_text(e.student.get_full_name()), smart_text(e))
        an = AssignmentNotificationFactory.create()
        self.assertIn(smart_text(an.user.get_full_name()), smart_text(an))
        self.assertIn(smart_text(an.student_assignment), smart_text(an))
        conn = CourseOfferingNewsNotificationFactory.create()
        self.assertIn(smart_text(conn.user.get_full_name()), smart_text(conn))
        self.assertIn(smart_text(conn.course_offering_news), smart_text(conn))


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
    spring_2015 = Semester(type='spring', year=2015)
    summer_2015 = Semester(type='summer', year=2015)
    autumn_2015 = Semester(type='autumn', year=2015)
    spring_2016 = Semester(type='spring', year=2016)
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


class CourseOfferingTests(TestCase):
    def test_by_semester(self):
        course = CourseFactory.create()
        for year in range(2013, 2018):
            CourseOfferingFactory.create(course=course,
                                         semester__year=year,
                                         semester__type='spring')
        self.assertEqual(CourseOffering.by_semester((2014, 'spring')).get(),
                         CourseOffering.objects
                         .filter(semester__year=2014,
                                 semester__type='spring')
                         .get())

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
        n_ongoing = sum((CourseOffering(course=CourseFactory(name="Test course"),
                                        semester=semester)
                         .in_current_term)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = lambda: (datetime.datetime(some_year, 11, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        n_ongoing = sum((CourseOffering(course=CourseFactory(name="Test course"),
                                        semester=semester)
                         .in_current_term)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = old_now


class CourseClassTests(TestCase):
    def test_slides_file_name(self):
        slide_fname = "foobar.pdf"
        cc = CourseClassFactory.create()
        fname = cc._slides_file_name(slide_fname)
        co = cc.course_offering
        self.assertIn(co.course.slug.replace("-", "_"), fname)
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
        self.assertEqual("Lecture", cc.type_display)

    def test_by_semester(self):
        c = CourseFactory.create()
        for year in range(2013, 2018):
            CourseClassFactory.create(course_offering__course=c,
                                      course_offering__semester__year=year,
                                      course_offering__semester__type='spring',
                                      slides=None)
        self.assertEqual(CourseClass.by_semester((2014, 'spring')).get(),
                         CourseClass.objects
                         .filter(course_offering__semester__year=2014,
                                 course_offering__semester__type='spring')
                         .get())
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
        co1 = CourseOfferingFactory.create()
        co2 = CourseOfferingFactory.create()
        a = AssignmentFactory.create(course_offering=co1)
        a_copy = Assignment.objects.filter(pk=a.pk).get()
        a_copy.course_offering = co2
        self.assertRaises(ValidationError, a_copy.clean)
        a_copy.course_offering = co1
        a_copy.save()
        a_copy.grade_min = a.grade_max + 1
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
        self.assertRegexpMatches(aa.file_name,
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
        as_.grade = as_.assignment.grade_max + 1
        self.assertRaises(ValidationError, as_.clean)
        as_.grade = as_.assignment.grade_max
        as_.save()

    def test_is_passed(self):
        u_student = StudentCenterFactory()
        u_teacher = TeacherCenterFactory()
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=True)
        # teacher comments first
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_teacher)
        as_.refresh_from_db()
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertTrue(as_.is_passed)
        # student comments first
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=True)
        as_.refresh_from_db()
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertTrue(as_.is_passed)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertTrue(as_.is_passed)
        # assignment is offline
        as_ = StudentAssignmentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=False)
        as_.refresh_from_db()
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(student_assignment=as_,
                                        author=u_student)
        as_.refresh_from_db()
        self.assertFalse(as_.is_passed)

    def test_student_assignment_state(self):
        import datetime
        from django.utils import timezone
        student = StudentCenterFactory()
        a_online = AssignmentFactory.create(
            grade_min=5, grade_max=10, is_online=True,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx = {'student': student, 'assignment': a_online}
        a_s = StudentAssignment(grade=0, **ctx)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = StudentAssignment(grade=4, **ctx)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = StudentAssignment(grade=5, **ctx)
        self.assertEqual(a_s.state, 'pass')
        a_s = StudentAssignment(grade=8, **ctx)
        self.assertEqual(a_s.state, 'good')
        a_s = StudentAssignment(grade=10, **ctx)
        self.assertEqual(a_s.state, 'excellent')
        a_s = StudentAssignment(**ctx)
        self.assertEqual(a_s.state, 'not_submitted')
        a_offline = AssignmentFactory.create(
            grade_min=5, grade_max=10, is_online=False,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx['assignment'] = a_offline
        a_s = StudentAssignment(**ctx)
        self.assertEqual(a_s.state, 'not_checked')

    def test_state_display(self):
        as_ = StudentAssignmentFactory(grade=30,
                                       assignment__grade_max=50)
        self.assertIn(smart_text(as_.assignment.grade_max), as_.state_display)
        self.assertIn(smart_text(as_.grade), as_.state_display)
        as_ = StudentAssignmentFactory(assignment__grade_max=50)
        self.assertEqual(as_.STATES['not_submitted'], as_.state_display)

    def test_state_short(self):
        as_ = StudentAssignmentFactory(grade=30,
                                       assignment__grade_max=50)
        self.assertIn(smart_text(as_.assignment.grade_max), as_.state_short)
        self.assertIn(smart_text(as_.grade), as_.state_short)
        as_ = StudentAssignmentFactory(assignment__grade_max=50)
        self.assertEqual(as_.SHORT_STATES['not_submitted'], as_.state_short)


class AssignmentCommentTests(TestCase):
    def test_attached_file(self):
        ac = AssignmentCommentFactory.create(
            attached_file__filename="foobar.pdf")
        self.assertIn(smart_text(ac.student_assignment.assignment.pk),
                      ac.attached_file.name)
        self.assertIn(smart_text(ac.student_assignment.student.pk),
                      ac.attached_file.name)
        self.assertRegexpMatches(ac.attached_file.name, "/foobar(_[0-9a-zA-Z]+)?.pdf$")
        self.assertRegexpMatches(ac.attached_file_name, "^foobar(_[0-9a-zA-Z]+)?.pdf$")


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
@pytest.mark.skip(reason="Monkey patching is totally broken")
# FIXME: We  need monkey patch timezone.now, but for that we should use utc, which use datetime. What a mess, fuck. I'll try to fix this later, now skip test
def test_course_offering_enrollment_expired(mocker, monkeypatch):
    current_year = 2015
    current_term_type = SEMESTER_TYPES.spring
    semester = SemesterFactory(year=current_year, type=current_term_type)
    co = CourseOfferingFactory.create(semester=semester)
    # Fixate spring semester term start
    enrollment_duration = 8
    monkeypatch.setattr("learning.settings.ENROLLMENT_DURATION", enrollment_duration)
    monkeypatch.setattr("learning.settings.SPRING_TERM_START", "10 jan")
    # Mock today time
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    import pytz
    start_datetime = datetime.datetime(current_year, month=1, day=10, tzinfo=pytz.utc)  # should be equal to term start
    mocked_timezone.return_value = start_datetime
    assert co.enrollment_is_open
    mocked_timezone.return_value = start_datetime + datetime.timedelta(days=enrollment_duration - 1)
    assert co.enrollment_is_open
    mocked_timezone.return_value = start_datetime + datetime.timedelta(days=enrollment_duration)
    assert co.enrollment_is_open
    mocked_timezone.return_value = start_datetime + datetime.timedelta(days=enrollment_duration + 1)
    assert not co.enrollment_is_open
    # Back to the future
    mocked_timezone.return_value = start_datetime - datetime.timedelta(days=enrollment_duration + 1)
    assert co.enrollment_is_open


@pytest.mark.django_db
def test_course_offering_manager_completed():
    """
    Make sure `completed` manager method considers `completed_at` as
    inclusive date.
    """
    today = now().date()
    semester = SemesterFactory.create_current()
    co = CourseOfferingFactory(completed_at=today, semester=semester)
    assert CourseOffering.objects.completed(True).count() == 1
    timedelta_1day = datetime.timedelta(days=1)
    CourseOfferingFactory.create_batch(2, completed_at=today + timedelta_1day,
                                       semester=semester)
    assert CourseOffering.objects.completed(True).count() == 1
    assert CourseOffering.objects.completed(False).count() == 2
