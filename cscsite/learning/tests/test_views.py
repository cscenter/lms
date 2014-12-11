# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import csv
import logging
import os

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from testfixtures import LogCapture

from django.conf import settings
from django.conf.urls.static import static
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test.utils import override_settings
from django.test import TestCase
from django.utils.encoding import smart_text

import cscsite.urls
from learning.utils import get_current_semester_pair
from .factories import *
from .mixins import *


class GroupSecurityCheckMixin(MyUtilitiesMixin):
    def test_group_security(self):
        """
        Checks if only users in groups listed in self.groups_allowed can
        access the page which url is stored in self.url_name.
        Also checks that superuser can access any page
        """
        # TODO: remove return
        # return
        self.assertTrue(self.groups_allowed is not None)
        self.assertTrue(self.url_name is not None)
        self.assertLoginRedirect(reverse(self.url_name))
        for groups in [[], ['Teacher'], ['Student'], ['Graduate']]:
            self.doLogin(UserFactory.create(groups=groups))
            if any(group in self.groups_allowed for group in groups):
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
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


@override_settings(TIME_ZONE='Etc/UTC')
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
        own_classes = (
            CourseClassFactory
            .create_batch(3, course_offering__teachers=[teacher],
                          date=this_month_date))
        others_classes = (
            CourseClassFactory
            .create_batch(5, course_offering__teachers=[other_teacher],
                          date=this_month_date))
        events = (
            NonCourseEventFactory
            .create_batch(2, date=this_month_date))
        # teacher should see only his own classes and non-course events
        resp = self.client.get(reverse(self.url_name))
        classes = self.calendar_month_to_object_list(resp.context['month'])
        self.assertSameObjects(own_classes + events, classes)
        # but in full calendar all classes should be shown
        classes = self.calendar_month_to_object_list(
            self.client.get(reverse('calendar_full_teacher')).context['month'])
        self.assertSameObjects(own_classes + others_classes + events, classes)
        next_month_qstr = (
            "?year={0}&month={1}"
            .format(resp.context['next_date'].year,
                    str(resp.context['next_date'].month).zfill(2)))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertSameObjects([], classes)
        next_month_date = this_month_date + relativedelta(months=1)
        next_month_classes = (
            CourseClassFactory
            .create_batch(2, course_offering__teachers=[teacher],
                          date=next_month_date))
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertSameObjects(next_month_classes, classes)


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
        own_classes = (
            CourseClassFactory
            .create_batch(3, course_offering=co, date=this_month_date))
        others_classes = (
            CourseClassFactory
            .create_batch(5, course_offering=co_other, date=this_month_date))
        # student should see only his own classes
        resp = self.client.get(reverse(self.url_name))
        classes = self.calendar_month_to_object_list(resp.context['month'])
        self.assertSameObjects(own_classes, classes)
        # but in full calendar all classes should be shown
        classes = self.calendar_month_to_object_list(
            self.client.get(reverse('calendar_full_student')).context['month'])
        self.assertSameObjects(own_classes + others_classes, classes)
        next_month_qstr = (
            "?year={0}&month={1}"
            .format(resp.context['next_date'].year,
                    str(resp.context['next_date'].month).zfill(2)))
        next_month_url = reverse(self.url_name) + next_month_qstr
        self.assertContains(resp, next_month_qstr)
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertSameObjects([], classes)
        next_month_date = this_month_date + relativedelta(months=1)
        next_month_classes = (
            CourseClassFactory
            .create_batch(2, course_offering=co, date=next_month_date))
        classes = self.calendar_month_to_object_list(
            self.client.get(next_month_url).context['month'])
        self.assertSameObjects(next_month_classes, classes)


class CalendarFullSecurityTests(MyUtilitiesMixin, TestCase):
    """
    This TestCase is used only for security check, actual tests for
    "full calendar" are done in CalendarTeacher/CalendarStudent tests
    """
    def test_full_calendar_security(self):
        u = UserFactory.create()
        for url in ['calendar_full_teacher', 'calendar_full_student']:
            self.assertLoginRedirect(reverse(url))
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
            self.assertPOSTLoginRedirect(url, {})
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
        self.assertLoginRedirect(url)
        self.doLogin(teacher_other)
        self.assertLoginRedirect(url)
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
        self.assertPOSTLoginRedirect(self.url, self.n_dict)
        self.doLogin(self.teacher_other)
        self.assertPOSTLoginRedirect(self.url, self.n_dict)
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
        self.assertPOSTLoginRedirect(self.url, self.con_dict)
        self.doLogin(self.teacher_other)
        self.assertPOSTLoginRedirect(self.url, self.con_dict)
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
        self.assertPOSTLoginRedirect(self.url, {})
        self.doLogin(self.teacher_other)
        self.assertPOSTLoginRedirect(self.url, {})
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
        url = reverse('course_class_add',
                      args=[co.course.slug, co.semester.slug])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)

    def test_create(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        co_other = CourseOfferingFactory.create(semester=s)
        form = CourseClassFactory.attributes()
        form.update({'venue': VenueFactory.create().pk})
        url = reverse('course_class_add',
                      args=[co.course.slug, co.semester.slug])
        self.doLogin(teacher)
        del form['course_offering']
        # should save with course_offering = co
        self.assertEqual(302, self.client.post(url, form).status_code)
        self.assertEqual(1, (CourseClass.objects
                             .filter(course_offering=co).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course_offering=co_other).count()))
        self.assertEqual(CourseClass.objects.get(course_offering=co).name,
                         form['name'])
        form.update({'course_offering': co.pk})
        self.assertEqual(302, self.client.post(url, form).status_code)

    def test_update(self):
        teacher = UserFactory.create(groups=['Teacher'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        url = reverse('course_class_edit',
                      args=[co.course.slug, co.semester.slug, cc.pk])
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
        url = reverse('course_class_delete',
                      args=[co.course.slug, co.semester.slug, cc.pk])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, {})
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
        base_url = reverse('course_class_edit',
                           args=[co.course.slug, co.semester.slug, cc.pk])
        self.doLogin(teacher)
        form = model_to_dict(cc)
        del form['slides']
        form['name'] += " foobar"
        self.assertRedirects(self.client.post(base_url, form),
                             cc.get_absolute_url())
        url = ("{}?back=course_offering"
               .format(base_url))
        self.assertRedirects(self.client.post(url, form),
                             co.get_absolute_url())

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
        url = reverse('course_class_edit',
                      args=[co.course.slug, co.semester.slug, cc.pk])
        resp = self.client.get(url)
        self.assertContains(resp,
                            reverse('course_class_attachment_delete',
                                    args=[co.course.slug, co.semester.slug,
                                          cc.pk, cca1.pk]))
        self.assertContains(resp, cca1.material_file_name)
        self.assertContains(resp,
                            reverse('course_class_attachment_delete',
                                    args=[co.course.slug, co.semester.slug,
                                          cc.pk, cca2.pk]))
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
        url = reverse('course_class_edit',
                      args=[co.course.slug, co.semester.slug, cc.pk])
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
                      args=[co.course.slug, co.semester.slug,
                            cc.pk, cca_to_delete.pk])
        # check security just in case
        self.doLogout()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, {})
        self.doLogin(teacher)
        self.assertContains(self.client.get(url),
                            cca_to_delete.material_file_name)
        self.assertRedirects(self.client.post(url),
                             reverse('course_class_edit',
                                     args=[co.course.slug,
                                           co.semester.slug,
                                           cc.pk]))
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
        self.assertLoginRedirect(url)
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Teacher']:
                self.assertEquals(403, self.client.get(url).status_code)
            else:
                self.assertLoginRedirect(url)
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


class ASStudentDetailTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_student', args=[a_s.pk])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Student']:
                # special case :(
                self.assertEquals(403, self.client.get(url).status_code)
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(teacher)
        self.assertLoginRedirect(url)
        self.doLogout()
        self.doLogin(student)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_assignment_contents(self):
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_student', args=[a_s.pk])
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.text)

    def test_comment(self):
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_student', args=[a_s.pk])
        comment_dict = {'text': "Test comment without file"}
        self.doLogin(student)
        self.assertRedirects(self.client.post(url, comment_dict), url)
        self.assertContains(self.client.get(url), comment_dict['text'])
        f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        comment_dict = {'text': "Test comment with file",
                        'attached_file': f}
        self.assertRedirects(self.client.post(url, comment_dict), url)
        resp = self.client.get(url)
        self.assertContains(resp, comment_dict['text'])
        self.assertContains(resp, 'attachment1')


class ASTeacherDetailTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Teacher']:
                self.assertEquals(403, self.client.get(url).status_code)
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)
        self.doLogout()
        self.doLogin(student)
        self.assertLoginRedirect(url)
        self.doLogout()
        grade_dict = {'grading_form': True,
                      'grade': 3}
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Teacher']:
                resp = self.client.post(url, grade_dict)
                self.assertEquals(403, resp.status_code)
            else:
                self.assertPOSTLoginRedirect(url, grade_dict)
            self.doLogout()

    def test_assignment_contents(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        self.doLogin(teacher)
        self.assertContains(self.client.get(url), a.text)

    def test_comment(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        comment_dict = {'text': "Test comment without file"}
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(url, comment_dict), url)
        self.assertContains(self.client.get(url), comment_dict['text'])
        f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        comment_dict = {'text': "Test comment with file",
                        'attached_file': f}
        self.assertRedirects(self.client.post(url, comment_dict), url)
        resp = self.client.get(url)
        self.assertContains(resp, comment_dict['text'])
        self.assertContains(resp, 'attachment1')

    def test_grading(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co,
                                     grade_max=13)
        a_s = (AssignmentStudent.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        grade_dict = {'grading_form': True,
                      'grade': 11}
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(url, grade_dict), url)
        self.assertEqual(11, AssignmentStudent.objects.get(pk=a_s.pk).grade)
        resp = self.client.get(url)
        self.assertContains(resp, "value=\"11\"")
        self.assertContains(resp, "/{}".format(13))
        # wrong grading value can't be set
        grade_dict['grade'] = 42
        self.client.post(url, grade_dict)
        self.assertEqual(400, self.client.post(url, grade_dict).status_code)
        self.assertEqual(11, AssignmentStudent.objects.get(pk=a_s.pk).grade)

    def test_next_unchecked(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        co_other = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        EnrollmentFactory.create(student=student, course_offering=co_other)
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        a_other = AssignmentFactory.create(course_offering=co_other)
        a_s1 = (AssignmentStudent.objects
                .filter(assignment=a1, student=student)
                .get())
        a_s2 = (AssignmentStudent.objects
                .filter(assignment=a2, student=student)
                .get())
        a_s_other = (AssignmentStudent.objects
                     .filter(assignment=a_other, student=student)
                     .get())
        url1 = reverse('a_s_detail_teacher', args=[a_s1.pk])
        url2 = reverse('a_s_detail_teacher', args=[a_s2.pk])
        self.doLogin(teacher)
        self.assertEqual(None, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(None, self.client.get(url2).context['next_a_s_pk'])
        [AssignmentCommentFactory.create(author=a_s.student,
                                         assignment_student=a_s)
         for a_s in [a_s1, a_s2]]
        self.assertEqual(a_s2.pk, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(a_s1.pk, self.client.get(url2).context['next_a_s_pk'])


class AssignmentCRUDTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = AssignmentFactory.attributes()
        form.update({'course_offering': co.pk,
                     'attached_file': None})
        url = reverse('assignment_add',
                      args=[co.course.slug, co.semester.slug])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        a = AssignmentFactory.create()
        url = reverse('assignment_edit',
                      args=[co.course.slug, co.semester.slug, a.pk])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups and groups[0] != 'Teacher':
                # NOTE(Dmitry): currently teachers CAN see other's assignments
                # through the edit form. However, it doesn't seem that bad
                # to me.
                self.assertLoginRedirect(url)
            if groups and groups[0] != 'Teacher':
                self.assertPOSTLoginRedirect(url, form)
            elif groups and groups[0] == 'Teacher':
                # Teacher will get 404
                self.assertEquals(404, self.client.post(url, form).status_code)
            self.doLogout()
        url = reverse('assignment_delete',
                      args=[co.course.slug, co.semester.slug, a.pk])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student'], ['Teacher']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()

    def test_create(self):
        teacher = UserFactory.create(groups=['Teacher'])
        CourseOfferingFactory.create_batch(3, teachers=[teacher])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = AssignmentFactory.attributes()
        deadline_date = form['deadline_at'].strftime("%Y-%m-%d")
        deadline_time = form['deadline_at'].strftime("%H:%M:%S")
        form.update({'course_offering': co.pk,
                     'attached_file': None,
                     'deadline_at_0': deadline_date,
                     'deadline_at_1': deadline_time})
        url = reverse('assignment_add',
                      args=[co.course.slug, co.semester.slug])
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(url, form),
                             co.get_absolute_url())

    def test_update(self):
        teacher = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a = AssignmentFactory.create(course_offering=co)
        form = model_to_dict(a)
        deadline_date = form['deadline_at'].strftime("%Y-%m-%d")
        deadline_time = form['deadline_at'].strftime("%H:%M:%S")
        form.update({'title': a.title + " foo42bar",
                     'course_offering': co.pk,
                     'attached_file': None,
                     'deadline_at_0': deadline_date,
                     'deadline_at_1': deadline_time})
        url = reverse('assignment_edit',
                      args=[co.course.slug, co.semester.slug, a.pk])
        list_url = reverse('assignment_list_teacher')
        self.doLogin(teacher)
        self.assertNotContains(self.client.get(list_url), form['title'])
        self.assertRedirects(self.client.post(url, form), co.get_absolute_url())
        self.assertContains(self.client.get(list_url), form['title'])

    def test_delete(self):
        teacher = UserFactory.create(groups=['Teacher'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a = AssignmentFactory.create(course_offering=co)
        url = reverse('assignment_delete',
                      args=[co.course.slug, co.semester.slug, a.pk])
        list_url = reverse('assignment_list_teacher')
        self.doLogin(teacher)
        self.assertContains(self.client.get(list_url), a.title)
        self.assertContains(self.client.get(url), a.title)
        self.assertRedirects(self.client.post(url), list_url)
        self.assertNotContains(self.client.get(list_url), a.title)


class MarksSheetTeacherTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'markssheet_teacher_dispatch'
    groups_allowed = ['Teacher']

    def test_redirect(self):
        teacher = UserFactory.create(groups=['Teacher'])
        students = UserFactory.create_batch(3, groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        url = reverse(self.url_name)
        co_url = reverse('markssheet_teacher',
                         args=[co.course.slug,
                               co.semester.year,
                               co.semester.type])
        self.assertRedirects(self.client.get(url), co_url)

    def test_list(self):
        teacher = UserFactory.create(groups=['Teacher'])
        students = UserFactory.create_batch(3, groups=['Student'])
        co1, co2 = CourseOfferingFactory.create_batch(2, teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        url = reverse(self.url_name)
        for co in [co1, co2]:
            co_url = reverse('markssheet_teacher',
                             args=[co.course.slug,
                                   co.semester.year,
                                   co.semester.type])
            self.assertContains(self.client.get(url), co_url)


class MarksSheetTeacherTests(MyUtilitiesMixin, TestCase):
    # TODO(Dmitry): test security

    def test_empty_markssheet(self):
        teacher = UserFactory.create(groups=['Teacher'])
        students = UserFactory.create_batch(3, groups=['Student'])
        co1 = CourseOfferingFactory.create(teachers=[teacher])
        co2 = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co1)
            EnrollmentFactory.create(student=student,
                                     course_offering=co2)
        url = reverse('markssheet_teacher', args=[co1.course.slug,
                                                  co1.semester.year,
                                                  co1.semester.type])
        self.doLogin(teacher)
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name, 1)
            field = 'final_grade_{}_{}'.format(co1.pk, student.pk)
            self.assertIn(field, resp.context['form'].fields)
        for co in [co1, co2]:
            url = reverse('markssheet_teacher',
                          args=[co.course.slug,
                                co.semester.year,
                                co.semester.type])
            self.assertContains(resp, url)

    def test_nonempty_markssheet(self):
        teacher = UserFactory.create(groups=['Teacher'])
        students = UserFactory.create_batch(3, groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        as_online = AssignmentFactory.create_batch(
            2, course_offering=co)
        as_offline = AssignmentFactory.create_batch(
            3, course_offering=co, is_online=False)
        url = reverse('markssheet_teacher', args=[co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
        self.doLogin(teacher)
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name)
        for as_ in as_online:
            self.assertContains(resp, as_.title)
            for student in students:
                a_s = AssignmentStudent.objects.get(student=student,
                                                    assignment=as_)
                a_s_url = reverse('a_s_detail_teacher', args=[a_s.pk])
                self.assertContains(resp, a_s_url)
        for as_ in as_offline:
            self.assertContains(resp, as_.title)
            for student in students:
                a_s = AssignmentStudent.objects.get(student=student,
                                                    assignment=as_)
                self.assertIn('a_s_{}'.format(a_s.pk),
                              resp.context['form'].fields)

    def test_save_markssheet(self):
        teacher = UserFactory.create(groups=['Teacher'])
        students = UserFactory.create_batch(2, groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co,
                                                is_online=False)
        url = reverse('markssheet_teacher', args=[co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
        self.doLogin(teacher)
        form = {}
        pairs = zip([AssignmentStudent.objects.get(student=student,
                                                   assignment=a)
                     for student in students
                     for a in [a1, a2]],
                    [2, 3, 4, 5])
        for a_s, grade in pairs:
            form['a_s_{}'.format(a_s.pk)] = grade
        for student in students:
            field = 'final_grade_{}_{}'.format(co.pk, student.pk)
            form[field] = 'good'
        self.assertRedirects(self.client.post(url, form), url)
        for a_s, grade in pairs:
            self.assertEqual(grade, (AssignmentStudent.objects
                                     .get(pk=a_s.pk)
                                     .grade))
        for student in students:
            self.assertEqual('good', (Enrollment.objects
                                      .get(student=student,
                                           course_offering=co)
                                      .grade))


class MarksSheetCSVTest(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student = UserFactory.create(groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        EnrollmentFactory.create(student=student, course_offering=co)
        url = reverse('markssheet_teacher_csv',
                      args=[co.course.slug, co.semester.slug])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student']]:
            self.doLogin(UserFactory.create(groups=groups))
        self.doLogin(UserFactory.create(groups=['Teacher']))
        self.assertEquals(404, self.client.get(url).status_code)
        self.doLogin(student)
        self.assertLoginRedirect(url)
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_csv(self):
        teacher = UserFactory.create(groups=['Teacher'])
        student1, student2 = UserFactory.create_batch(2, groups=['Student'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        [EnrollmentFactory.create(student=s, course_offering=co)
         for s in [student1, student2]]
        url = reverse('markssheet_teacher_csv',
                      args=[co.course.slug, co.semester.slug])
        combos = [(a, s, grade+1)
                  for ((a, s), grade)
                  in zip([(a, s)
                          for a in [a1, a2]
                          for s in [student1, student2]],
                         range(4))]
        for a, s, grade in combos:
            a_s = AssignmentStudent.objects.get(student=s, assignment=a)
            a_s.grade = grade
            a_s.save()
        self.doLogin(teacher)
        data = [[x.decode('utf8') if isinstance(x, basestring) else x
                 for x in row]
                for row in csv.reader(self.client.get(url)) if row]
        self.assertEquals(3, len(data))
        self.assertIn(a1.title, data[0])
        row_last_names = [row[0] for row in data]
        for a, s, grade in combos:
            row = row_last_names.index(s.last_name)
            col = data[0].index(a.title)
            self.assertEquals(grade, int(data[row][col]))


class MarksSheetStaffTests(GroupSecurityCheckMixin,
                           MyUtilitiesMixin, TestCase):
    url_name = 'markssheet_staff'
    groups_allowed = []

    def test_nonempty_markssheet(self):
        students = UserFactory.create_batch(3, groups=['Student'])
        cos = CourseOfferingFactory.create_batch(2)
        for student in students:
            for co in cos:
                EnrollmentFactory.create(student=student,
                                         course_offering=co)
        as_online = AssignmentFactory.create_batch(
            2, course_offering=co)
        as_offline = AssignmentFactory.create_batch(
            3, course_offering=co, is_online=False)
        url = reverse(self.url_name)
        self.doLogin(UserFactory.create(is_superuser=True))
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name)
        for co in cos:
            self.assertContains(resp, smart_text(co.course))

    def test_enrollment_year(self):
        student1 = UserFactory.create(groups=['Student'],
                                      enrollment_year=2012)
        student2 = UserFactory.create(groups=['Student'],
                                      enrollment_year=2013)
        cos = CourseOfferingFactory.create_batch(2)
        for student in [student1, student2]:
            for co in cos:
                EnrollmentFactory.create(student=student,
                                         course_offering=co)
        url = reverse(self.url_name)
        self.doLogin(UserFactory.create(is_superuser=True))
        resp = self.client.get(url)
        self.assertSameObjects([2012, 2013], resp.context['enrollment_years'])
        self.assertContains(resp, student1.last_name)
        self.assertContains(resp, student2.last_name)
        resp = self.client.get(url + "?enrollment_year=2012")
        self.assertContains(resp, student1.last_name)
        self.assertNotContains(resp, student2.last_name)


class NonCourseEventDetailTests(MyUtilitiesMixin, TestCase):
    def basic_test(self):
        evt = NonCourseEventFactory.create()
        url = cc.get_absolute_url()
        resp = self.client.get(url)
        self.assertContains(evt.name, resp)
        self.assertContains(evt.venue.get_absolute_url(), resp)
