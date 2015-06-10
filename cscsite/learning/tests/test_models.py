# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os

from mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.encoding import smart_text

from .factories import *


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
        as_ = AssignmentStudentFactory.create()
        self.assertIn(smart_text(as_.student.get_full_name()), smart_text(as_))
        self.assertIn(smart_text(as_.assignment), smart_text(as_))
        ac = AssignmentCommentFactory.create()
        self.assertIn(smart_text(ac.assignment_student.assignment),
                      smart_text(ac))
        self.assertIn(smart_text(ac.assignment_student
                                 .student.get_full_name()),
                      smart_text(ac))
        e = EnrollmentFactory.create()
        self.assertIn(smart_text(e.course_offering), smart_text(e))
        self.assertIn(smart_text(e.student.get_full_name()), smart_text(e))
        an = AssignmentNotificationFactory.create()
        self.assertIn(smart_text(an.user.get_full_name()), smart_text(an))
        self.assertIn(smart_text(an.assignment_student), smart_text(an))
        conn = CourseOfferingNewsNotificationFactory.create()
        self.assertIn(smart_text(conn.user.get_full_name()), smart_text(conn))
        self.assertIn(smart_text(conn.course_offering_news), smart_text(conn))


class SemesterTests(TestCase):
    def test_starts_ends(self):
        spring_date = (datetime.datetime(2015, 4, 8, 0, 0, 0)
                       .replace(tzinfo=timezone.utc))
        autumn_date = (datetime.datetime(2015, 11, 8, 0, 0, 0)
                       .replace(tzinfo=timezone.utc))
        next_spring_date = (datetime.datetime(2016, 4, 8, 0, 0, 0)
                            .replace(tzinfo=timezone.utc))
        semester = Semester(type='spring', year=2015)
        self.assertLess(semester.starts_at, spring_date)
        self.assertLess(spring_date, semester.ends_at)
        self.assertLess(semester.ends_at, autumn_date)
        semester = Semester(type='autumn', year=2015)
        self.assertLess(semester.starts_at, autumn_date)
        self.assertLess(autumn_date, semester.ends_at)
        self.assertLess(semester.ends_at, next_spring_date)

    def test_semester_cmp(self):
        s2013_spring = Semester(type='spring', year=2013)
        s2013_autumn = Semester(type='autumn', year=2013)
        s2013_summer = Semester(type='summer', year=2013)
        s2014_spring = Semester(type='spring', year=2014)
        self.assertLess(s2013_spring, s2013_autumn)
        self.assertLess(s2013_spring, s2013_summer)
        self.assertLess(s2013_summer, s2013_autumn)
        self.assertLess(s2013_summer, s2014_spring)

    def test_type_index(self):
        spring_index = 0
        summer_index = 1
        autumn_index = 2
        semester = Semester(type='spring', year=2013)
        self.assertEqual(semester.type_index, spring_index)
        semester.type = 'summer'
        self.assertEqual(semester.type_index, summer_index)
        semester.type = 'autumn'
        self.assertEqual(semester.type_index, autumn_index)



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

    def test_is_ongoing(self):
        """
        In near future only one course should be "ongoing".
        """
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
                         .is_ongoing)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = lambda: (datetime.datetime(some_year, 11, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        n_ongoing = sum((CourseOffering(course=CourseFactory(name="Test course"),
                                        semester=semester)
                         .is_ongoing)
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

    @patch('learning.slides.upload_to_slideshare')
    @patch('learning.slides.upload_to_yandex')
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
        a = AssignmentFactory.create()
        self.assertTrue(a.is_open)
        a.deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                         - datetime.timedelta(days=1))
        self.assertFalse(a.is_open)


class AssignmentAttachmentTest(TestCase):
    def test_attached_file_name(self):
        fname = "foobar.pdf"
        aa = AssignmentAttachmentFactory.create(attachment__filename=fname)
        self.assertRegexpMatches(aa.attachment_file_name,
                                 "^foobar(_[0-9a-zA-Z]+)?.pdf$")


class AssignmentStudentTests(TestCase):
    def test_clean(self):
        u1 = UserFactory.create(groups=['Student'])
        u2 = UserFactory.create(groups=[])
        as_ = AssignmentStudentFactory.create(student=u1)
        as_.student = u2
        self.assertRaises(ValidationError, as_.clean)
        as_.student = u1
        as_.save()
        as_.grade = as_.assignment.grade_max + 1
        self.assertRaises(ValidationError, as_.clean)
        as_.grade = as_.assignment.grade_max
        as_.save()

    def test_is_passed(self):
        u_student = UserFactory.create(groups=['Student'])
        u_teacher = UserFactory.create(groups=['Teacher'])
        as_ = AssignmentStudentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=True)
        # teacher comments first
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_teacher)
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertTrue(as_.is_passed)
        # student comments first
        as_ = AssignmentStudentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=True)
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertTrue(as_.is_passed)
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertTrue(as_.is_passed)
        # assignment is offline
        as_ = AssignmentStudentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=False)
        self.assertFalse(as_.is_passed)
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertFalse(as_.is_passed)

    def test_assignment_student_state(self):
        student = UserFactory.create(groups=['Student'])
        a_online = AssignmentFactory.create(
            grade_min=5, grade_max=10, is_online=True,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx = {'student': student, 'assignment': a_online}
        a_s = AssignmentStudent(grade=0, **ctx)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = AssignmentStudent(grade=4, **ctx)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = AssignmentStudent(grade=5, **ctx)
        self.assertEqual(a_s.state, 'pass')
        a_s = AssignmentStudent(grade=8, **ctx)
        self.assertEqual(a_s.state, 'good')
        a_s = AssignmentStudent(grade=10, **ctx)
        self.assertEqual(a_s.state, 'excellent')
        a_s = AssignmentStudent(**ctx)
        self.assertEqual(a_s.state, 'not_submitted')
        a_offline = AssignmentFactory.create(
            grade_min=5, grade_max=10, is_online=False,
            deadline_at=datetime.datetime.now().replace(tzinfo=timezone.utc)
        )
        ctx['assignment'] = a_offline
        a_s = AssignmentStudent(**ctx)
        self.assertEqual(a_s.state, 'not_checked')

    def test_state_display(self):
        as_ = AssignmentStudentFactory(grade=30,
                                       assignment__grade_max=50)
        self.assertIn(smart_text(as_.assignment.grade_max), as_.state_display)
        self.assertIn(smart_text(as_.grade), as_.state_display)
        as_ = AssignmentStudentFactory(assignment__grade_max=50)
        self.assertEqual(as_.STATES['not_submitted'], as_.state_display)

    def test_state_short(self):
        as_ = AssignmentStudentFactory(grade=30,
                                       assignment__grade_max=50)
        self.assertIn(smart_text(as_.assignment.grade_max), as_.state_short)
        self.assertIn(smart_text(as_.grade), as_.state_short)
        as_ = AssignmentStudentFactory(assignment__grade_max=50)
        self.assertEqual(as_.SHORT_STATES['not_submitted'], as_.state_short)


class AssignmentCommentTests(TestCase):
    def test_attached_file(self):
        ac = AssignmentCommentFactory.create(
            attached_file__filename="foobar.pdf")
        self.assertIn(smart_text(ac.assignment_student.assignment.pk),
                      ac.attached_file.name)
        self.assertIn(smart_text(ac.assignment_student.student.pk),
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
            user=UserFactory.create(groups=['Student']),
            is_about_passed=True)
        self.assertRaises(ValidationError, an.clean)
