# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime
import logging
import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test.client import Client
from django.test import TestCase
from django.utils.encoding import smart_text
from django.utils import timezone

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
import factory
from mock import patch
from testfixtures import LogCapture

import cscsite.urls
from .models import Course, Semester, CourseOffering, CourseOfferingNews, \
    Assignment, Venue, CourseClass, CourseClassAttachment, AssignmentStudent, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    CourseOfferingNewsNotification
from .utils import get_current_semester_pair
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
    # TODO: create course offering for current semester by default

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
    title = factory.Sequence(lambda n: "Imporant news about testing %03d" % n)
    author = factory.SubFactory(UserFactory, groups=['Teacher'])
    text = factory.Sequence(lambda n: ("Suddenly it turned out that testing "
                                       "(%03d) can be useful!" % n))


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
    name = factory.Sequence(lambda n: "Test class %03d" % n)
    description = factory.Sequence(
        lambda n: "In this class %03d we will test" % n)
    slides = factory.django.FileField()
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
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
    def assertStatusCode(self, code, url_name, make_reverse=True, **kwargs):
        if make_reverse:
            url = reverse(url_name, **kwargs)
        else:
            url = url_name
        self.assertEqual(code, self.client.get(url).status_code)

    def assertSameObjects(self, obj_list1, obj_list2):
        self.assertEqual(set(obj_list1), set(obj_list2))

    def doLogin(self, user):
        self.assertTrue(self.client.login(username=user.username,
                                          password=user.raw_password))

    def doLogout(self):
        self.client.logout()

    def calendar_month_to_object_list(self, calendar_month):
        return [x
                for week in calendar_month
                for day in week[1]
                for x in day[1]]


class MediaServingMixin(object):
    def setUp(self):
        self._original_urls = cscsite.urls.urlpatterns
        with self.settings(DEBUG=True):
            s = static(settings.MEDIA_URL,
                       document_root=settings.MEDIA_ROOT)
            cscsite.urls.urlpatterns += s

    def tearDown(self):
        cscsite.urls.urlpatterns = self._original_urls


class GroupSecurityCheckMixin(MyUtilitiesMixin):
    def test_group_security(self):
        """
        Checks if only users in groups listed in self.groups_allowed can
        access the page which url is stored in self.url_name.
        Also checks that superuser can access any page
        """
        # TODO: remove return
        return
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


class CalendarTeacherTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, TestCase):
    url_name = 'calendar_teacher'
    groups_allowed = ['Teacher']

    def test_teacher_calendar(self):
        teacher = UserFactory.create(groups=['Teacher'])
        other_teacher = UserFactory.create(groups=['Teacher'])
        self.doLogin(teacher)
        classes = self.calendar_month_to_object_list(
            self.client.get(reverse(self.url_name)).context['month'])
        self.assertEqual(0, len(classes))
        this_month_date = (datetime.datetime.now()
                           .replace(day=15,
                                    tzinfo=timezone.utc))
        CourseClassFactory.create_batch(3, course_offering__teachers=[teacher],
                                        date=this_month_date)
        # teacher should see only his own classes
        CourseClassFactory\
            .create_batch(5, course_offering__teachers=[other_teacher],
                          date=this_month_date)
        resp = self.client.get(reverse(self.url_name))
        classes = self.calendar_month_to_object_list(resp.context['month'])
        self.assertEqual(3, len(classes))
        # but in full calendar all classes should be shown
        classes = self.calendar_month_to_object_list(
            self.client.get(reverse('calendar_full_student')).context['month'])
        self.assertEqual(8, len(classes))
        next_month_qstr = ("?year={0}&month={1}"
                           .format(resp.context['next_date'].year,
                                   resp.context['next_date'].month))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertEqual(0, len(classes))
        next_month_date = this_month_date + relativedelta(months=1)
        CourseClassFactory\
            .create_batch(2, course_offering__teachers=[teacher],
                          date=next_month_date)
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertEqual(2, len(classes))


class CalendarStudentTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, TestCase):
    url_name = 'calendar_student'
    groups_allowed = ['Student']

    def test_student_calendar(self):
        student = UserFactory.create(groups=['Student'])
        self.doLogin(student)
        co = CourseOfferingFactory.create()
        co_other = CourseOfferingFactory.create()
        e = EnrollmentFactory.create(course_offering=co, student=student)
        classes = self.calendar_month_to_object_list(
            self.client.get(reverse(self.url_name)).context['month'])
        self.assertEqual(0, len(classes))
        this_month_date = (datetime.datetime.now()
                           .replace(day=15,
                                    tzinfo=timezone.utc))
        CourseClassFactory.create_batch(3, course_offering=co,
                                        date=this_month_date)
        # student should see only his own classes
        CourseClassFactory.create_batch(5, course_offering=co_other,
                                        date=this_month_date)
        resp = self.client.get(reverse(self.url_name))
        classes = self.calendar_month_to_object_list(resp.context['month'])
        self.assertEqual(3, len(classes))
        # but in full calendar all classes should be shown
        classes = self.calendar_month_to_object_list(
            self.client.get(reverse('calendar_full_student')).context['month'])
        self.assertEqual(8, len(classes))
        next_month_qstr = ("?year={0}&month={1}"
                           .format(resp.context['next_date'].year,
                                   resp.context['next_date'].month))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertEqual(0, len(classes))
        next_month_date = this_month_date + relativedelta(months=1)
        CourseClassFactory.create_batch(2, course_offering=co,
                                        date=next_month_date)
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertEqual(2, len(classes))


class CalendarFullSecurityTests(MyUtilitiesMixin, TestCase):
    """
    This TestCase is used only for security check, actual tests for
    "full calendar" are done in CalendarTeacher/CalendarStudent tests
    """
    def test_full_calendar_security(self):
        u = UserFactory.create()
        for url in ['calendar_full_teacher', 'calendar_full_student']:
            self.assertStatusCode(403, url)
            self.doLogin(u)  # those URLs are LoginRequired-only
            self.assertStatusCode(200, url)
            self.client.logout()


class SemesterListTests(MyUtilitiesMixin, TestCase):
    def cos_from_semester_list(self, lst):
        return sum([semester.courseofferings
                    for pair in lst
                    for semester in pair
                    if semester], [])

    def test_semester_list(self):
        cos = self.cos_from_semester_list(
            self.client.get(reverse('course_list'))
            .context['semester_list'])
        self.assertEqual(0, len(cos))
        # Microoptimization: avoid creating teachers/courses
        u = UserFactory.create(groups=['Teacher'])
        c = CourseFactory.create()
        for semester_type in ['autumn', 'spring']:
            for year in range(2012, 2015):
                s = SemesterFactory.create(type=semester_type,
                                           year=year)
                CourseOfferingFactory.create(course=c, semester=s,
                                             teachers=[u])
        s = SemesterFactory.create(type='autumn', year=2015)
        CourseOfferingFactory.create(course=c, semester=s, teachers=[u])
        resp = self.client.get(reverse('course_list'))
        self.assertEqual(4, len(resp.context['semester_list']))
        # dummy semester object should be present for 2016 spring
        self.assertEqual(0, len(resp.context['semester_list'][0][1]
                                .courseofferings))
        cos = self.cos_from_semester_list(resp.context['semester_list'])
        self.assertEqual(7, len(cos))


class CourseListTeacherTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'course_list_teacher'
    groups_allowed = ['Teacher']

    def test_teacher_course_list(self):
        teacher = UserFactory.create(groups=['Teacher'])
        other_teacher = UserFactory.create(groups=['Teacher'])
        self.doLogin(teacher)
        resp = self.client.get(reverse(self.url_name))
        self.assertEqual(0, len(resp.context['course_list_ongoing']))
        self.assertEqual(0, len(resp.context['course_list_archive']))
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        CourseOfferingFactory.create_batch(
            3, teachers=[teacher], semester=s)
        CourseOfferingFactory.create_batch(
            2, teachers=[teacher, other_teacher], semester=s)
        CourseOfferingFactory.create_batch(
            4, teachers=[other_teacher], semester=s)
        CourseOfferingFactory.create(teachers=[teacher],
                                     semester__year=now_year-1)
        resp = self.client.get(reverse(self.url_name))
        teacher_url = reverse('teacher_detail', args=[teacher.pk])
        self.assertContains(resp, teacher_url, count=5+1)
        self.assertEqual(5, len(resp.context['course_list_ongoing']))
        self.assertEqual(1, len(resp.context['course_list_archive']))


class CourseListStudentTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'course_list_student'
    groups_allowed = ['Student']

    def test_student_course_list(self):
        student = UserFactory.create(groups=['Student'])
        other_student = UserFactory.create(groups=['Student'])
        self.doLogin(student)
        resp = self.client.get(reverse(self.url_name))
        self.assertEqual(0, len(resp.context['course_list_ongoing']))
        self.assertEqual(0, len(resp.context['course_list_available']))
        self.assertEqual(0, len(resp.context['course_list_archive']))
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        cos = CourseOfferingFactory.create_batch(4, semester=s)
        cos_available = cos[:2]
        cos_enrolled = cos[2:]
        for co in cos_enrolled:
            EnrollmentFactory.create(student=student, course_offering=co)
        cos_archived = CourseOfferingFactory.create_batch(
            3, semester__year=now_year-1)
        resp = self.client.get(reverse(self.url_name))
        self.assertSameObjects(cos_enrolled,
                               resp.context['course_list_ongoing'])
        self.assertSameObjects(cos_available,
                               resp.context['course_list_available'])


class CourseDetailTests(MyUtilitiesMixin, TestCase):
    def test_course_detail(self):
        c = CourseFactory.create()
        CourseOfferingFactory.create_batch(2, course=c)
        resp = self.client.get(c.get_absolute_url())
        self.assertContains(resp, c.name)
        self.assertContains(resp, c.description)
        self.assertSameObjects(resp.context['offerings'],
                               c.courseoffering_set.all())


class CourseUpdateTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        c = CourseFactory.create()
        url = reverse('course_edit', args=[c.slug])
        for groups in [[], ['Teacher'], ['Student'], ['Graduate']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertEqual(403, self.client.post(url).status_code)
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True))
        self.assertEqual(
            200, self.client.post(url, {'name': "foobar"}).status_code)

    def test_update(self):
        c = CourseFactory.create()
        url = reverse('course_edit', args=[c.slug])
        self.doLogin(UserFactory.create(is_superuser=True))
        fields = model_to_dict(c)
        fields.update({'name': "foobar"})
        self.assertEqual(302, self.client.post(url, fields).status_code)
        self.assertEqual("foobar", Course.objects.get(pk=c.pk).name)


class CourseOfferingDetailTests(MyUtilitiesMixin, TestCase):
    def test_basic_get(self):
        co = CourseOfferingFactory.create()
        self.assertEqual(
            200, self.client.get(co.get_absolute_url()).status_code)
        url = reverse('course_offering_detail', args=["space-odyssey", "2010"])
        self.assertEqual(404, self.client.get(url).status_code)

    def test_course_user_relations(self):
        """
        Testing is_enrolled and is_actual_teacher here
        """
        student = UserFactory.create(groups=['Student'])
        teacher = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create()
        co_other = CourseOfferingFactory.create()
        url = co.get_absolute_url()
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        self.doLogin(student)
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        EnrollmentFactory.create(student=student, course_offering=co_other)
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        EnrollmentFactory.create(student=student, course_offering=co)
        ctx = self.client.get(url).context
        self.assertEqual(True, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        self.client.logout()
        self.doLogin(teacher)
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        co_other.teachers.add(teacher)
        co_other.save()
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        co.teachers.add(teacher)
        co.save()
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(True, ctx['is_actual_teacher'])

    def test_assignment_list(self):
        student = UserFactory.create(groups=['Student'])
        teacher = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        url = co.get_absolute_url()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        self.assertNotContains(self.client.get(url), a.title)
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.title)
        a_s = AssignmentStudent.objects.get(assignment=a, student=student)
        self.assertContains(self.client.get(url),
                            reverse('a_s_detail_student', args=[a_s.pk]))
        a_s.delete()
        with LogCapture(level=logging.INFO) as l:
            self.assertEqual(200, self.client.get(url).status_code)
            l.check(('learning.views',
                     'ERROR',
                     "can't find AssignmentStudent for "
                     "student ID {0}, assignment ID {1}"
                     .format(student.pk, a.pk)))
        self.client.logout()
        self.doLogin(teacher)
        self.assertContains(self.client.get(url), a.title)
        self.assertContains(self.client.get(url),
                            reverse('assignment_detail_teacher', args=[a.pk]))


class CourseOfferingEditDescrTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        teacher_other = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        url = reverse('course_offering_edit_descr',
                      args=[co.course.slug, co.semester.slug])
        self.assertStatusCode(403, url, make_reverse=False)
        self.doLogin(teacher_other)
        self.assertStatusCode(403, url, make_reverse=False)
        self.doLogout()
        self.doLogin(teacher)
        self.assertStatusCode(200, url, make_reverse=False)


class CourseOfferingNewsCreateTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = UserFactory.create(groups=['Teacher'])
        self.teacher_other = UserFactory.create(groups=['Teacher'])
        self.co = CourseOfferingFactory.create(teachers=[self.teacher])
        self.url = reverse('course_offering_news_create',
                           args=[self.co.course.slug,
                                 self.co.semester.slug])
        self.n_dict = CourseOfferingNewsFactory.attributes()
        self.n_dict.update({'course_offering': self.co})

    def test_security(self):
        self.assertEqual(
            403, self.client.post(self.url, self.n_dict).status_code)
        self.doLogin(self.teacher_other)
        self.assertEqual(
            403, self.client.post(self.url, self.n_dict).status_code)
        self.doLogout()
        self.doLogin(self.teacher)
        self.assertEqual(
            302, self.client.post(self.url, self.n_dict).status_code)

    def test_news_creation(self):
        co_url = self.co.get_absolute_url()
        self.doLogin(self.teacher)
        self.assertRedirects(
            self.client.post(self.url, self.n_dict), co_url)
        resp = self.client.get(co_url)
        self.assertContains(resp, self.n_dict['text'])
        con = resp.context['course_offering'].courseofferingnews_set.all()[0]
        self.assertEqual(con.author, self.teacher)


class CourseOfferingNewsUpdateTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = UserFactory.create(groups=['Teacher'])
        self.teacher_other = UserFactory.create(groups=['Teacher'])
        self.co = CourseOfferingFactory.create(teachers=[self.teacher])
        self.con = CourseOfferingNewsFactory.create(course_offering=self.co,
                                                    author=self.teacher)
        self.url = reverse('course_offering_news_update',
                           args=[self.co.course.slug,
                                 self.co.semester.slug,
                                 self.con.pk])
        self.con_dict = model_to_dict(self.con)
        self.con_dict.update({'text': "foobar text"})

    def test_security(self):
        self.assertEqual(
            403, self.client.post(self.url, self.con_dict).status_code)
        self.doLogin(self.teacher_other)
        self.assertEqual(
            403, self.client.post(self.url, self.con_dict).status_code)
        self.doLogout()
        self.doLogin(self.teacher)
        self.assertEqual(
            302, self.client.post(self.url, self.con_dict).status_code)

    def test_news_update(self):
        self.doLogin(self.teacher)
        co_url = self.co.get_absolute_url()
        self.assertRedirects(
            self.client.post(self.url, self.con_dict), co_url)
        self.assertContains(self.client.get(co_url), self.con_dict['text'])


class CourseOfferingNewsDeleteTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = UserFactory.create(groups=['Teacher'])
        self.teacher_other = UserFactory.create(groups=['Teacher'])
        self.co = CourseOfferingFactory.create(teachers=[self.teacher])
        self.con = CourseOfferingNewsFactory.create(course_offering=self.co,
                                                    author=self.teacher)
        self.url = reverse('course_offering_news_delete',
                           args=[self.co.course.slug,
                                 self.co.semester.slug,
                                 self.con.pk])

    def test_security(self):
        self.assertEqual(403, self.client.post(self.url).status_code)
        self.doLogin(self.teacher_other)
        self.assertEqual(403, self.client.post(self.url).status_code)
        self.doLogout()
        self.doLogin(self.teacher)
        self.assertEqual(302, self.client.post(self.url).status_code)

    def test_news_delete(self):
        self.doLogin(self.teacher)
        co_url = self.co.get_absolute_url()
        self.assertRedirects(self.client.post(self.url), co_url)
        self.assertNotContains(self.client.get(co_url), self.con.text)


class CourseOfferingEnrollmentTests(MyUtilitiesMixin, TestCase):
    def test_enrollment(self):
        s = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create()
        co_other = CourseOfferingFactory.create()
        as_ = AssignmentFactory.create_batch(3, course_offering=co)
        self.doLogin(s)
        url = reverse('course_offering_enroll',
                      args=[co.course.slug, co.semester.slug])
        form = {'course_offering_pk': co.pk}
        self.assertRedirects(self.client.post(url, form),
                             co.get_absolute_url())
        self.assertEquals(1, Enrollment.objects
                          .filter(student=s, course_offering=co)
                          .count())
        self.assertEquals(set((s.pk, a.pk) for a in as_),
                          set(AssignmentStudent.objects
                              .filter(student=s)
                              .values_list('student', 'assignment')))
        form.update({'back': 'course_list_student'})
        url = reverse('course_offering_enroll',
                      args=[co_other.course.slug, co_other.semester.slug])
        self.assertRedirects(self.client.post(url, form),
                             reverse('course_list_student'))

    def test_unenrollment(self):
        s = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create()
        as_ = AssignmentFactory.create_batch(3, course_offering=co)
        form = {'course_offering_pk': co.pk}
        url = reverse('course_offering_unenroll',
                      args=[co.course.slug, co.semester.slug])
        self.doLogin(s)
        self.client.post(reverse('course_offering_enroll',
                                 args=[co.course.slug, co.semester.slug]),
                         form)
        resp = self.client.get(url)
        self.assertContains(resp, "Unenroll")
        self.assertContains(resp, smart_text(co))
        self.client.post(url, form)
        self.assertEquals(0, Enrollment.objects
                          .filter(student=s, course_offering=co)
                          .count())
        self.assertEquals(0, (AssignmentStudent.objects
                              .filter(student=s,
                                      assignment__course_offering=co)
                              .count()))
        self.client.post(reverse('course_offering_enroll',
                                 args=[co.course.slug, co.semester.slug]),
                         form)
        url += "?back=course_list_student"
        self.assertRedirects(self.client.post(url, form),
                             reverse('course_list_student'))


class CourseClassDetailTests(MyUtilitiesMixin, TestCase):
    def test_is_actual_teacher(self):
        teacher = UserFactory.create(groups=['Teacher'])
        cc = CourseClassFactory.create()
        cc_other = CourseClassFactory.create()
        url = cc.get_absolute_url()
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        self.doLogin(teacher)
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        cc_other.course_offering.teachers.add(teacher)
        cc_other.course_offering.save()
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        cc.course_offering.teachers.add(teacher)
        cc.course_offering.save()
        self.assertEqual(True, self.client.get(url)
                         .context['is_actual_teacher'])


class CourseClassDetailCRUDTests(MediaServingMixin,
                                 MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = CourseClassFactory.attributes()
        form.update({'venue': VenueFactory.create().pk})
        url = reverse('course_class_add')
        self.assertEqual(403, self.client.get(url).status_code)
        self.assertEqual(403, self.client.post(url, form).status_code)

    def test_create(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        co_other = CourseOfferingFactory.create(semester=s)
        form = CourseClassFactory.attributes()
        form.update({'venue': VenueFactory.create().pk})
        url = reverse('course_class_add')
        self.doLogin(teacher)
        form.update({'course_offering': co_other.pk})
        # should show an error instead of 302
        self.assertEqual(200, self.client.post(url, form).status_code)
        form.update({'course_offering': co.pk})
        self.assertEqual(302, self.client.post(url, form).status_code)
        self.assertEqual(CourseClass.objects.get(course_offering=co).name,
                         form['name'])

    def test_update(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        url = reverse('course_class_edit', args=[cc.pk])
        self.doLogin(teacher)
        form = model_to_dict(cc)
        del form['slides']
        form['name'] += " foobar"
        self.assertRedirects(self.client.post(url, form),
                             cc.get_absolute_url())
        self.assertEquals(form['name'],
                          self.client.get(cc.get_absolute_url())
                          .context['object'].name)

    def test_delete(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        url = reverse('course_class_delete', args=[cc.pk])
        self.assertEquals(403, self.client.get(url).status_code)
        self.assertEquals(403, self.client.post(url).status_code)
        self.doLogin(teacher)
        self.assertContains(self.client.get(url), smart_text(cc))
        self.assertRedirects(self.client.post(url),
                             reverse('timetable_teacher'))
        self.assertFalse(CourseClass.objects.filter(pk=cc.pk).exists())

    def test_back_variable(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        base_url = reverse('course_class_edit', args=[cc.pk])
        self.doLogin(teacher)
        form = model_to_dict(cc)
        del form['slides']
        form['name'] += " foobar"
        self.assertRedirects(self.client.post(base_url, form),
                             cc.get_absolute_url())
        url = ("{}?back=course_offering&course_offering={}"
               .format(base_url, co.pk))
        self.assertRedirects(self.client.post(url, form),
                             co.get_absolute_url())
        url = ("{}?back=course_offering&course_offering={}"
               .format(base_url, "foobar"))
        self.assertEquals(404, self.client.post(url, form).status_code)
        url = ("{}?back=course_offering&course_offering={}"
               .format(base_url, 424242))
        self.assertEquals(404, self.client.post(url, form).status_code)
        url = "{}?back=calendar".format(base_url, co.pk)
        self.assertRedirects(self.client.post(url, form),
                             reverse('calendar_teacher'))
        url = "{}?back=timetable".format(base_url, co.pk)
        self.assertRedirects(self.client.post(url, form),
                             reverse('timetable_teacher'))

    def test_attachment_links(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        cca1 = CourseClassAttachmentFactory.create(
            course_class=cc, material__filename="foobar1.pdf")
        cca2 = CourseClassAttachmentFactory.create(
            course_class=cc, material__filename="foobar2.zip")
        resp = self.client.get(cc.get_absolute_url())
        self.assertContains(resp, cca1.material.url)
        self.assertContains(resp, cca1.material_file_name)
        self.assertContains(resp, cca2.material.url)
        self.assertContains(resp, cca2.material_file_name)
        self.doLogin(teacher)
        resp = self.client.get(reverse('course_class_edit', args=[cc.pk]))
        self.assertContains(resp, reverse('course_class_attachment_delete',
                                          args=[cc.pk, cca1.pk]))
        self.assertContains(resp, cca1.material_file_name)
        self.assertContains(resp, reverse('course_class_attachment_delete',
                                          args=[cc.pk, cca2.pk]))
        self.assertContains(resp, cca2.material_file_name)

    def test_attachments(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        f1 = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        f2 = SimpleUploadedFile("attachment2.txt", b"attachment2_content")
        self.doLogin(teacher)
        form = model_to_dict(cc)
        del form['slides']
        form['attachments'] = [f1, f2]
        url = reverse('course_class_edit', args=[cc.pk])
        self.assertRedirects(self.client.post(url, form),
                             cc.get_absolute_url())
        # check that files are available from course class page
        resp = self.client.get(cc.get_absolute_url())
        spans = (BeautifulSoup(resp.content)
                 .find_all('span', class_='assignment-attachment'))
        self.assertEquals(2, len(spans))
        cca_files = sorted(a.material.path
                           for a in resp.context['attachments'])
        # we will delete attachment2.txt
        cca_to_delete = [a for a in resp.context['attachments']
                         if a.material.path == cca_files[1]][0]
        as_ = sorted((span.a.contents[0].strip(),
                      "".join(self.client.get(span.a['href'])
                              .streaming_content))
                     for span in spans)
        self.assertRegexpMatches(as_[0][0], "attachment1(_\d+)?.txt")
        self.assertRegexpMatches(as_[1][0], "attachment2(_\d+)?.txt")
        self.assertEquals(as_[0][1], b"attachment1_content")
        self.assertEquals(as_[1][1], b"attachment2_content")
        # delete one of the files, check that it's deleted and other isn't
        url = reverse('course_class_attachment_delete',
                      args=[cc.pk, cca_to_delete.pk])
        # check security just in case
        self.doLogout()
        self.assertEquals(403, self.client.get(url).status_code)
        self.assertEquals(403, self.client.post(url).status_code)
        self.doLogin(teacher)
        self.assertContains(self.client.get(url),
                            cca_to_delete.material_file_name)
        self.assertRedirects(self.client.post(url),
                             reverse('course_class_edit', args=[cc.pk]))
        resp = self.client.get(cc.get_absolute_url())
        spans = (BeautifulSoup(resp.content)
                 .find_all('span', class_='assignment-attachment'))
        self.assertEquals(1, len(spans))
        self.assertRegexpMatches(spans[0].a.contents[0].strip(),
                                 "attachment1(_\d+)?.txt")
        self.assertFalse(os.path.isfile(cca_files[1]))


class AssignmentStudentListTests(GroupSecurityCheckMixin,
                                 MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_student'
    groups_allowed = ['Student']

    def test_list(self):
        u = UserFactory.create(groups=['Student'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(semester=s)
        as1 = AssignmentFactory.create_batch(2, course_offering=co)
        self.doLogin(u)
        # no assignments yet
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # enroll at course offering, assignments are shown
        EnrollmentFactory.create(student=u, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(2, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # add a few assignments, they should show up
        as2 = AssignmentFactory.create_batch(3, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertSameObjects([(AssignmentStudent.objects
                                 .get(assignment=a, student=u))
                                for a in (as1 + as2)],
                               resp.context['assignment_list_open'])
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # add a few old assignments, they should show up in archive
        deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                       - datetime.timedelta(days=1))
        as3 = AssignmentFactory.create_batch(2, course_offering=co,
                                             deadline_at=deadline_at)
        resp = self.client.get(reverse(self.url_name))
        for a in as1 + as2 + as3:
            self.assertContains(resp, a.title)
        self.assertSameObjects([(AssignmentStudent.objects
                                 .get(assignment=a, student=u))
                                for a in (as1 + as2)],
                               resp.context['assignment_list_open'])
        self.assertSameObjects([(AssignmentStudent.objects
                                 .get(assignment=a, student=u))
                                for a in as3],
                               resp.context['assignment_list_archive'])


class AssignmentTeacherListTests(GroupSecurityCheckMixin,
                                 MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_teacher'
    groups_allowed = ['Teacher']

    def test_list(self):
        teacher = UserFactory.create(groups=['Teacher'])
        students = UserFactory.create_batch(3, groups=['Student'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        # some other teacher's course offering
        co_other = CourseOfferingFactory.create(semester=s)
        AssignmentFactory.create_batch(2, course_offering=co_other)
        self.doLogin(teacher)
        # no assignments yet
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # assignments should show up in archive
        co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
        as1 = AssignmentFactory.create_batch(2, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertSameObjects(as1, resp.context['assignment_list_archive'])
        resp = self.client.get(reverse(self.url_name) + "?show_all=true")
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertSameObjects(as1, resp.context['assignment_list_archive'])
        # enroll students, their assignments should show up only in
        # "show all" mode
        for student in students:
            EnrollmentFactory.create(student=student, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertSameObjects(as1, resp.context['assignment_list_archive'])
        resp = self.client.get(reverse(self.url_name) + "?show_all=true")
        self.assertSameObjects([(AssignmentStudent.objects
                                 .get(student=student,
                                      assignment=assignment))
                                for student in students
                                for assignment in as1],
                               resp.context['assignment_list_open'])
        self.assertSameObjects(as1, resp.context['assignment_list_archive'])
        # teacher commented on an assingnment, it still shouldn't show up
        a = as1[0]
        student = students[0]
        a_s = AssignmentStudent.objects.get(student=student, assignment=a)
        AssignmentCommentFactory.create(assignment_student=a_s,
                                        author=teacher)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        # but if student have commented, it should show up
        AssignmentCommentFactory.create(assignment_student=a_s,
                                        author=student)
        resp = self.client.get(reverse(self.url_name))
        self.assertSameObjects([a_s], resp.context['assignment_list_open'])
        # if teacher has set a grade, assignment shouldn't show up
        a_s.grade = 3
        a_s.save()
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))


class AssignmentTeacherDetailsTest(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        a = AssignmentFactory.create(course_offering__teachers=[teacher])
        url = reverse('assignment_detail_teacher', args=[a.pk])
        self.assertEquals(403, self.client.get(url).status_code)
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertEquals(403, self.client.get(url).status_code)
            self.doLogout()
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_details(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
        a = AssignmentFactory.create(course_offering=co)
        self.doLogin(teacher)
        url = reverse('assignment_detail_teacher', args=[a.pk])
        resp = self.client.get(url)
        self.assertEquals(a, resp.context['assignment'])
        self.assertEquals(0, len(resp.context['a_s_list']))
        EnrollmentFactory.create(student=student, course_offering=co)
        a_s = AssignmentStudent.objects.get(student=student, assignment=a)
        resp = self.client.get(url)
        self.assertEquals(a, resp.context['assignment'])
        self.assertSameObjects([a_s], resp.context['a_s_list'])


# TODO: notifications test
# TODO: smoke test
# TODO: smoke security test
# TODO: smoke numquery test
