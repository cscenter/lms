# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime
import os

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.encoding import smart_text
from django.utils import timezone

import factory
from mock import patch

from .models import Course, Semester, CourseOffering, CourseOfferingNews, \
    Assignment, Venue, CourseClass, \
    AssignmentStudent
from users.models import CSCUser


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = CSCUser

    username = factory.Sequence(lambda n: "testuser%03d" % n)
    password = "test123foobar@!"
    email = "user@foobar.net"

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group_name in extracted:
                self.groups.add(Group.objects.get(name=group_name))


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    name = "Test course"
    slug = "test-course"
    description = "This a course for testing purposes"


class SemesterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Semester

    year = 2015
    type = Semester().TYPES['spring']


class CourseOfferingFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOffering

    course = factory.SubFactory(CourseFactory)
    semester = factory.SubFactory(SemesterFactory)
    description = "This course offering will be very different"

    # TODO: add "enrolled students" here

    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for teacher in extracted:
                self.teachers.add(teacher)


class CourseOfferingNewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingNews

    course_offering = factory.SubFactory(CourseOfferingFactory)
    title = "Imporant news about testing"
    author = factory.SubFactory(UserFactory, groups=['Teacher'])
    text = "Suddenly it turned out that testing can be useful!"


class VenueFactory(factory.DjangoModelFactory):
    class Meta:
        model = Venue

    name = "Test venue"
    description = "This is a special venue for tests"


class CourseClassFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseClass

    course_offering = factory.SubFactory(CourseOfferingFactory)
    venue = factory.SubFactory(VenueFactory)
    type = 'lecture'
    name = "Test class"
    description = "In this class we will test"
    slides = factory.django.FileField()
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3))
    starts_at = "13:00"
    ends_at = "13:45"


# Model tests


class CommonTests(TestCase):
    def test_to_strings(self):
        course = CourseFactory.build()
        self.assertEquals(smart_text(course), course.name)
        semester = Semester(year=2015, type='spring')
        self.assertIn(smart_text(semester.year), smart_text(semester))
        self.assertIn('spring', smart_text(semester))
        co = CourseOfferingFactory.build()
        self.assertIn(smart_text(co.course), smart_text(co))
        self.assertIn(smart_text(co.semester), smart_text(co))
        con = CourseOfferingNewsFactory.build()
        self.assertIn(smart_text(con.title), smart_text(con))
        self.assertIn(smart_text(con.course_offering), smart_text(con))
        cc = CourseClassFactory.build()
        self.assertIn(cc.name, smart_text(cc))


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
        old_now = timezone.now
        timezone.now = lambda: (datetime.datetime(some_year, 4, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        n_ongoing = sum((CourseOffering(course=Course(name="Test course"),
                                        semester=semester)
                         .is_ongoing)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = lambda: (datetime.datetime(some_year, 11, 8, 0, 0, 0)
                                .replace(tzinfo=timezone.utc))
        n_ongoing = sum((CourseOffering(course=Course(name="Test course"),
                                        semester=semester)
                         .is_ongoing)
                        for semester in semesters)
        self.assertEqual(n_ongoing, 1)
        timezone.now = old_now


class CourseClassTests(TestCase):
    def test_slides_file_name(self):
        slide_fname = "foobar.pdf"
        cc = CourseClassFactory.build()
        fname = cc._slides_file_name(slide_fname)
        co = cc.course_offering
        self.assertIn(co.course.slug.replace("-", "_"), fname)
        self.assertIn(co.semester.slug.replace("-", "_"), fname)
        _, ext = os.path.splitext(slide_fname)
        self.assertIn(ext, fname)

    def test_start_end_validation(self):
        time1 = "13:00"
        time2 = "14:20"
        cc = CourseClassFactory.build(starts_at=time1, ends_at=time2)
        self.assertEqual(None, cc.clean())
        cc = CourseClassFactory.build(starts_at=time2, ends_at=time1)
        self.assertRaises(ValidationError, cc.clean)

    def test_display_prop(self):
        cc = CourseClassFactory.build(type='lecture')
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
        cc = CourseClassFactory.create()
        self.assertIn("/", cc.slides.name)
        self.assertNotIn("/", cc.slides_file_name)
        self.assertTrue(upload_to_slideshare.called)
        self.assertTrue(upload_to_yandex.called)


class AssignmentStudentTests(TestCase):
    def test_assignment_student_state(self):
        """
        Testing AssignmentStudent#state logic (it's nontrivial)
        """
        student = CSCUser()
        student.save()
        student.groups = [student.IS_STUDENT_PK]
        student.save()
        a_online = Assignment(grade_min=5, grade_max=10, is_online=True)
        ctx = {'student': student, 'assignment': a_online}
        a_s = AssignmentStudent(grade=0, **ctx)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = AssignmentStudent(grade=4, **ctx)
        self.assertEqual(a_s.state, 'unsatisfactory')
        a_s = AssignmentStudent(grade=5, **ctx)
        self.assertEqual(a_s.state, 'pass')
        a_s = AssignmentStudent(grade=10, **ctx)
        self.assertEqual(a_s.state, 'excellent')
        a_s = AssignmentStudent(**ctx)
        self.assertEqual(a_s.state, 'not_submitted')
        a_offline = Assignment(grade_min=5, grade_max=10, is_online=False)
        ctx['assignment'] = a_offline
        a_s = AssignmentStudent(**ctx)
        self.assertEqual(a_s.state, 'not_checked')
