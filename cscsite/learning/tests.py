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

from dateutil.relativedelta import relativedelta
import factory
from mock import patch

from .models import Course, Semester, CourseOffering, CourseOfferingNews, \
    Assignment, Venue, CourseClass, CourseClassAttachment, AssignmentStudent, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    CourseOfferingNewsNotification
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

    @factory.post_generation
    def raw_password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = self.password
        self.set_password(raw_password)
        self.save()
        self.raw_password = raw_password


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Sequence(lambda n: "Test course %03d" % n)
    slug = factory.Sequence(lambda n: "test-course-%03d" % n)
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

    @classmethod
    def build(cls, *args, **kwargs):
        if all('slides_' not in key for key in kwargs.keys()):
            kwargs['slides'] = None
        return super(CourseClassFactory, cls).build(*args, **kwargs)

    @classmethod
    def create(cls, *args, **kwargs):
        if all('slides_' not in key for key in kwargs.keys()):
            kwargs['slides'] = None
        return super(CourseClassFactory, cls).create(*args, **kwargs)


class CourseClassAttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseClassAttachment

    course_class = factory.SubFactory(CourseClassFactory)
    material = factory.django.FileField()


class AssignmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Assignment

    course_offering = factory.SubFactory(CourseOfferingFactory)
    # TODO(Dmitry): add assigned_to
    deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                   + datetime.timedelta(days=1))
    is_online = True
    title = factory.Sequence(lambda n: "Test assignment %03d" % n)
    text = "This is a text for a test assignment"
    attached_file = factory.django.FileField()
    grade_min = 10
    grade_max = 80


class AssignmentStudentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentStudent

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory, groups=['Student'])


class AssignmentCommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentComment

    assignment_student = factory.SubFactory(AssignmentStudentFactory)
    text = factory.Sequence(lambda n: "Test comment %03d" % n)
    author = factory.SubFactory(UserFactory)
    attached_file = factory.django.FileField()


class EnrollmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Enrollment

    student = factory.SubFactory(UserFactory, groups=['Student'])
    course_offering = factory.SubFactory(CourseOfferingFactory)


class AssignmentNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentNotification

    user = factory.SubFactory(UserFactory)
    assignment_student = factory.SubFactory(AssignmentStudentFactory)


class CourseOfferingNewsNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingNewsNotification

    user = factory.SubFactory(UserFactory)
    course_offering_news = factory.SubFactory(CourseOfferingNewsFactory)


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
        cca = (CourseClassAttachmentFactory
               .build(material__filename="foobar.pdf"))
        self.assertIn("foobar", smart_text(cca))
        self.assertIn("pdf", smart_text(cca))
        a = AssignmentFactory.build()
        self.assertIn(a.title, smart_text(a))
        self.assertIn(smart_text(a.course_offering), smart_text(a))
        as_ = AssignmentStudentFactory.build()
        self.assertIn(smart_text(as_.student), smart_text(as_))
        self.assertIn(smart_text(as_.assignment), smart_text(as_))
        ac = AssignmentCommentFactory.create()
        self.assertIn(smart_text(ac.assignment_student.assignment),
                      smart_text(ac))
        self.assertIn(smart_text(ac.assignment_student
                                 .student.get_full_name()),
                      smart_text(ac))
        e = EnrollmentFactory.build()
        self.assertIn(smart_text(e.course_offering), smart_text(e))
        self.assertIn(smart_text(e.student), smart_text(e))
        an = AssignmentNotificationFactory.build()
        self.assertIn(smart_text(an.user.get_full_name()), smart_text(an))
        self.assertIn(smart_text(an.assignment_student), smart_text(an))
        conn = CourseOfferingNewsNotificationFactory.build()
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

    def test_attached_file_name(self):
        fname = "foobar.pdf"
        a = AssignmentFactory.create(attached_file__filename=fname)
        self.assertRegexpMatches(a.attached_file_name, "^foobar(_\d+)?.pdf$")


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

    def test_has_passes(self):
        u_student = UserFactory.create(groups=['Student'])
        u_teacher = UserFactory.create(groups=['Teacher'])
        # TODO(Dmitry): enrollment should be correct here
        as_ = AssignmentStudentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=True)
        # teacher comments first
        self.assertFalse(as_.has_passes())
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_teacher)
        self.assertFalse(as_.has_passes())
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertTrue(as_.has_passes())
        # student comments first
        as_ = AssignmentStudentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=True)
        self.assertFalse(as_.has_passes())
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertTrue(as_.has_passes())
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertTrue(as_.has_passes())
        # assignment is offline
        as_ = AssignmentStudentFactory(
            student=u_student,
            assignment__course_offering__teachers=[u_teacher],
            assignment__is_online=False)
        self.assertFalse(as_.has_passes())
        AssignmentCommentFactory.create(assignment_student=as_,
                                        author=u_student)
        self.assertFalse(as_.has_passes())

    def test_assignment_student_state(self):
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
        a_s = AssignmentStudent(grade=8, **ctx)
        self.assertEqual(a_s.state, 'good')
        a_s = AssignmentStudent(grade=10, **ctx)
        self.assertEqual(a_s.state, 'excellent')
        a_s = AssignmentStudent(**ctx)
        self.assertEqual(a_s.state, 'not_submitted')
        a_offline = Assignment(grade_min=5, grade_max=10, is_online=False)
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
    def test_atttached_file(self):
        ac = AssignmentCommentFactory.create(
            attached_file__filename="foobar.pdf")
        self.assertIn(smart_text(ac.assignment_student.assignment.pk),
                      ac.attached_file.name)
        self.assertIn(smart_text(ac.assignment_student.student.pk),
                      ac.attached_file.name)
        self.assertRegexpMatches(ac.attached_file.name, "/foobar(_\d+)?.pdf$")
        self.assertRegexpMatches(ac.attached_file_name, "^foobar(_\d+)?.pdf$")


class EnrollmentTests(TestCase):
    def test_clean(self):
        e = EnrollmentFactory.build(student=UserFactory.create())
        self.assertRaises(ValidationError, e.clean)


class AssignmentNotificationTests(TestCase):
    def test_clean(self):
        an = AssignmentNotificationFactory.build(
            user=UserFactory.create(groups=['Student']),
            is_about_passed=True)
        self.assertRaises(ValidationError, an.clean)


# View tests


class MyUtilitiesMixin(object):
    def assertStatusCode(self, code, url_name):
        self.assertEqual(code,
                         self.client.get(reverse(url_name)).status_code)

    def doLogin(self, user):
        self.assertTrue(self.client.login(username=user.username,
                                          password=user.raw_password))


class GroupSecurityCheckMixin(MyUtilitiesMixin):
    def test_group_security(self):
        """
        Checks if only users in groups listed in self.groups_allowed can
        access the page which url is stored in self.url_name.
        Also checks that superuser can access any page
        """
        self.assertTrue(self.groups_allowed is not None)
        self.assertTrue(self.url_name is not None)
        self.assertStatusCode(403, self.url_name)
        for groups in [[], ['Teacher'], ['Student'], ['Graduate']]:
            self.doLogin(UserFactory.create(groups=groups))
            if any(group in self.groups_allowed for group in groups):
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertStatusCode(403, self.url_name)
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True))
        self.assertStatusCode(200, self.url_name)


class TimetableTeacherTests(GroupSecurityCheckMixin,
                            MyUtilitiesMixin, TestCase):
    url_name = 'timetable_teacher'
    groups_allowed = ['Teacher']

    def test_teacher_timetable(self):
        teacher = UserFactory.create(groups=['Teacher'])
        self.doLogin(teacher)
        self.assertEqual(0, len(self.client.get(reverse('timetable_teacher'))
                                .context['object_list']))
        today_date = (datetime.datetime.now().replace(tzinfo=timezone.utc))
        CourseClassFactory.create_batch(3, course_offering__teachers=[teacher],
                                        date=today_date)
        resp = self.client.get(reverse('timetable_teacher'))
        self.assertEqual(3, len(resp.context['object_list']))
        next_month_qstr = ("?year={0}&month={1}"
                           .format(resp.context['next_date'].year,
                                   resp.context['next_date'].month))
        next_month_url = reverse('timetable_teacher') + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        self.assertEqual(0, len(self.client.get(next_month_url)
                                .context['object_list']))
        next_month_date = today_date + relativedelta(months=1)
        CourseClassFactory.create_batch(2, course_offering__teachers=[teacher],
                                        date=next_month_date)
        self.assertEqual(2, len(self.client.get(next_month_url)
                                .context['object_list']))


class TimetableStudentTests(GroupSecurityCheckMixin,
                            MyUtilitiesMixin, TestCase):
    url_name = 'timetable_student'
    groups_allowed = ['Student']

    def test_student_timetable(self):
        student = UserFactory.create(groups=['Student'])
        self.doLogin(student)
        co = CourseOfferingFactory.create()
        e = EnrollmentFactory.create(course_offering=co, student=student)
        self.assertEqual(0, len(self.client.get(reverse('timetable_student'))
                                .context['object_list']))
        today_date = (datetime.datetime.now().replace(tzinfo=timezone.utc))
        CourseClassFactory.create_batch(3, course_offering=co, date=today_date)
        resp = self.client.get(reverse('timetable_student'))
        self.assertEqual(3, len(resp.context['object_list']))
        next_week_qstr = ("?year={0}&week={1}"
                          .format(resp.context['next_year'],
                                  resp.context['next_week']))
        next_week_url = reverse('timetable_student') + next_week_qstr
        self.assertContains(resp, next_week_qstr)
        self.assertEqual(0, len(self.client.get(next_week_url)
                                .context['object_list']))
        next_week_date = today_date + relativedelta(weeks=1)
        CourseClassFactory.create_batch(2, course_offering=co,
                                        date=next_week_date)
        self.assertEqual(2, len(self.client.get(next_week_url)
                                .context['object_list']))
