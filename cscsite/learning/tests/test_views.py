# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import os
import pytest
import re
import unicodecsv
import unittest

import pytest
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
from django.utils.encoding import smart_text, force_text, force_str, smart_bytes
from django.utils.translation import ugettext as _
from learning.settings import GRADES, GRADING_TYPES, GRADING_TYPES
from ..utils import get_current_semester_pair
from ..factories import *
from .mixins import *
from learning.forms import MarksSheetTeacherImportGradesForm


class GroupSecurityCheckMixin(MyUtilitiesMixin):
    def test_group_security(self):
        """
        Checks if only users in groups listed in self.groups_allowed can
        access the page which url is stored in self.url_name.
        Also checks that curator can access any page
        """
        # TODO: remove return
        # return
        self.assertTrue(self.groups_allowed is not None)
        self.assertTrue(self.url_name is not None)
        self.assertLoginRedirect(reverse(self.url_name))
        for groups in [[], ['Teacher [CENTER]'], ['Student [CENTER]'], ['Graduate']]:
            self.doLogin(UserFactory.create(groups=groups))
            if any(group in self.groups_allowed for group in groups):
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        self.assertStatusCode(200, self.url_name)


class TimetableTeacherTests(GroupSecurityCheckMixin,
                            MyUtilitiesMixin, TestCase):
    url_name = 'timetable_teacher'
    groups_allowed = ['Teacher [CENTER]']

    def test_teacher_timetable(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
    groups_allowed = ['Student [CENTER]']

    def test_student_timetable(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
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
    groups_allowed = ['Teacher [CENTER]']

    def test_teacher_calendar(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        other_teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
    groups_allowed = ['Student [CENTER]']

    def test_student_calendar(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
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
        u = UserFactory.create(groups=['Teacher [CENTER]'])
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


class CourseVideoListTests(MyUtilitiesMixin, TestCase):
    def test_video_list(self):
        cos_no_video = (CourseOfferingFactory
                        .create_batch(2, is_published_in_video=False))
        cos_video = (CourseOfferingFactory
                     .create_batch(5, is_published_in_video=True))
        resp = self.client.get(reverse('course_video_list'))
        chunks = resp.context['course_list_chunks']
        self.assertEqual(3, len(chunks[0]))
        self.assertEqual(2, len(chunks[1]))
        self.assertSameObjects(cos_video,
                               [co for chunk in chunks for co in chunk])



class CourseListTeacherTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'course_list_teacher'
    groups_allowed = ['Teacher [CENTER]']

    def test_teacher_course_list(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        other_teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        self.assertContains(resp, teacher_url, count=5)
        self.assertEqual(5, len(resp.context['course_list_ongoing']))
        self.assertEqual(1, len(resp.context['course_list_archive']))


class CourseListStudentTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'course_list_student'
    groups_allowed = ['Student [CENTER]']

    def test_student_course_list(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        other_student = UserFactory.create(groups=['Student [CENTER]'])
        self.doLogin(student)
        resp = self.client.get(reverse(self.url_name))
        self.assertEqual(0, len(resp.context['course_list_available']))
        self.assertEqual(0, len(resp.context['enrollments_ongoing']))
        self.assertEqual(0, len(resp.context['enrollments_archive']))
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        cos = CourseOfferingFactory.create_batch(4, semester=s)
        cos_available = cos[:2]
        cos_enrolled = cos[2:]
        enrollments_ongoing = []
        enrollments_archive = []
        cos_archived = CourseOfferingFactory.create_batch(
            3, semester__year=now_year-1)
        for co in cos_enrolled:
            enrollments_ongoing.append(
                EnrollmentFactory.create(student=student,
                                         course_offering=co))
        for co in cos_archived:
            enrollments_archive.append(
                EnrollmentFactory.create(student=student,
                                         course_offering=co))
        resp = self.client.get(reverse(self.url_name))
        self.assertSameObjects(enrollments_ongoing,
                               resp.context['enrollments_ongoing'])
        self.assertSameObjects(enrollments_archive,
                               resp.context['enrollments_archive'])
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
        for groups in [[], ['Teacher [CENTER]'], ['Student [CENTER]'], ['Graduate']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertPOSTLoginRedirect(url, {})
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        self.assertEqual(
            200, self.client.post(url, {'name': "foobar"}).status_code)

    def test_update(self):
        c = CourseFactory.create()
        url = reverse('course_edit', args=[c.slug])
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        fields = model_to_dict(c)
        # Note: Create middleware for lang request support in cscenter app
        # or define locale value explicitly
        fields.update({'name_ru': "foobar"})
        self.assertEqual(302, self.client.post(url, fields).status_code)
        self.assertEqual("foobar", Course.objects.get(pk=c.pk).name_ru)


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
        student = UserFactory.create(groups=['Student [CENTER]'])
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        CourseOfferingTeacherFactory(course_offering=co_other, teacher=teacher)
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        CourseOfferingTeacherFactory(course_offering=co, teacher=teacher)
        ctx = self.client.get(url).context
        self.assertEqual(False, ctx['is_enrolled'])
        self.assertEqual(True, ctx['is_actual_teacher'])

    def test_assignment_list(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        url = co.get_absolute_url()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        self.assertNotContains(self.client.get(url), a.title)
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.title)
        a_s = StudentAssignment.objects.get(assignment=a, student=student)
        self.assertContains(self.client.get(url),
                            reverse('a_s_detail_student', args=[a_s.pk]))
        a_s.delete()
        with LogCapture(level=logging.INFO) as l:
            self.assertEqual(200, self.client.get(url).status_code)
            l.check(('learning.views',
                     'ERROR',
                     "can't find StudentAssignment for "
                     "student ID {0}, assignment ID {1}"
                     .format(student.pk, a.pk)))
        self.client.logout()
        self.doLogin(teacher)
        self.assertContains(self.client.get(url), a.title)
        self.assertContains(self.client.get(url),
                            reverse('assignment_detail_teacher', args=[a.pk]))


class CourseOfferingEditDescrTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        teacher_other = UserFactory.create(groups=['Teacher [CENTER]'])
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
        self.teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        self.teacher_other = UserFactory.create(groups=['Teacher [CENTER]'])
        self.co = CourseOfferingFactory.create(teachers=[self.teacher])
        self.url = reverse('course_offering_news_create',
                           args=[self.co.course.slug,
                                 self.co.semester.slug])
        self.n_dict = CourseOfferingNewsFactory.attributes(create=True)
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
        self.teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        self.teacher_other = UserFactory.create(groups=['Teacher [CENTER]'])
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
        self.teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        self.teacher_other = UserFactory.create(groups=['Teacher [CENTER]'])
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


class CourseOfferingMultiSiteSecurityTests(MyUtilitiesMixin, TestCase):
    def test_list_center_site(self):
        """Center students can see club CO only from SPB"""
        current_semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(semester=current_semester,
                                          city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseOfferingFactory.create(semester=current_semester,
                                          city="RU KZN")
        resp = self.client.get(reverse('course_list'))
        self.assertContains(resp, co.course.name)
        self.assertNotContains(resp, co_kzn.course.name)
        # Note: Club related tests in csclub app

    def test_student_list_center_site(self):
        s = UserFactory.create(groups=['Student [CENTER]'])
        self.doLogin(s)
        current_semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(semester=current_semester,
                                          city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseOfferingFactory.create(semester=current_semester,
                                          city="RU KZN")
        resp = self.client.get(reverse('course_list_student'))
        self.assertEqual(len(resp.context['course_list_available']), 1)


class CourseClassDetailTests(MyUtilitiesMixin, TestCase):
    def test_is_actual_teacher(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        cc = CourseClassFactory.create()
        cc_other = CourseClassFactory.create()
        url = cc.get_absolute_url()
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        self.doLogin(teacher)
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        CourseOfferingTeacherFactory(course_offering=cc_other.course_offering,
                                     teacher=teacher)
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        CourseOfferingTeacherFactory(course_offering=cc.course_offering,
                                     teacher=teacher)
        self.assertEqual(True, self.client.get(url)
                         .context['is_actual_teacher'])

    @unittest.skip('not implemented yet')
    def test_show_news_only_to_authorized(self):
        """ On cscenter site only authorized users can see news """
        pass


class CourseClassDetailCRUDTests(MediaServingMixin,
                                 MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = CourseClassFactory.attributes(create=True)
        form.update({'venue': VenueFactory.create().pk})
        url = reverse('course_class_add',
                      args=[co.course.slug, co.semester.slug])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)

    def test_create(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        co_other = CourseOfferingFactory.create(semester=s)
        form = CourseClassFactory.attributes(create=True)
        form.update({'venue': VenueFactory.create().pk})
        del form['slides']
        url = reverse('course_class_add',
                      args=[co.course.slug, co.semester.slug])
        self.doLogin(teacher)
        # should save with course_offering = co
        self.assertEqual(302, self.client.post(url, form).status_code)
        self.assertEqual(1, (CourseClass.objects
                             .filter(course_offering=co).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course_offering=co_other).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course_offering=form['course_offering']).count()))
        self.assertEqual(CourseClass.objects.get(course_offering=co).name,
                         form['name'])
        form.update({'course_offering': co.pk})
        self.assertEqual(302, self.client.post(url, form).status_code)

    def test_create_and_add(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        co_other = CourseOfferingFactory.create(semester=s)
        form = CourseClassFactory.attributes(create=True)
        form.update({'venue': VenueFactory.create().pk, '_addanother': True})
        del form['slides']
        self.doLogin(teacher)
        url = reverse('course_class_add',
                      args=[co.course.slug, co.semester.slug])
        # should save with course_offering = co
        response = self.client.post(url, form)
        expected_url = reverse('course_class_add', args=[co.course.slug,
                                                         co.semester.slug])
        self.assertEqual(302, response.status_code)
        self.assertRedirects(response, expected_url)
        self.assertEqual(1, (CourseClass.objects
                             .filter(course_offering=co).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course_offering=co_other).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course_offering=form['course_offering']).count()))
        self.assertEqual(CourseClass.objects.get(course_offering=co).name,
                         form['name'])
        form.update({'course_offering': co.pk})
        self.assertEqual(302, self.client.post(url, form).status_code)
        del form['_addanother']
        response = self.client.post(url, form)
        self.assertEqual(3, (CourseClass.objects
                             .filter(course_offering=co).count()))
        last_added_class = CourseClass.objects.order_by("-id").first()
        self.assertRedirects(response, last_added_class.get_absolute_url())

    def test_update(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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

    def test_update_and_add(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        form.update({'_addanother': True})
        expected_url = reverse('course_class_add',
                      args=[co.course.slug, co.semester.slug])
        self.assertRedirects(self.client.post(url, form), expected_url)

    def test_delete(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
        response = self.client.get(cc.get_absolute_url())
        spans = (BeautifulSoup(response.content, "html.parser")
                 .find_all('span', class_='assignment-attachment'))
        self.assertEquals(2, len(spans))
        cca_files = sorted(a.material.path
                           for a in response.context['attachments'])
        # we will delete attachment2.txt
        cca_to_delete = [a for a in response.context['attachments']
                         if a.material.path == cca_files[1]][0]
        as_ = sorted((span.a.contents[0].strip(),
                      b"".join(self.client.get(span.a['href']).streaming_content))
                     for span in spans)
        self.assertRegexpMatches(as_[0][0], "attachment1(_[0-9a-zA-Z]+)?.txt")
        self.assertRegexpMatches(as_[1][0], "attachment2(_[0-9a-zA-Z]+)?.txt")
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
        response = self.client.get(cc.get_absolute_url())
        spans = (BeautifulSoup(response.content, "html.parser")
                 .find_all('span', class_='assignment-attachment'))
        self.assertEquals(1, len(spans))
        self.assertRegexpMatches(spans[0].a.contents[0].strip(),
                                 "attachment1(_[0-9a-zA-Z]+)?.txt")
        self.assertFalse(os.path.isfile(cca_files[1]))


class StudentAssignmentListTests(GroupSecurityCheckMixin,
                                 MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_student'
    groups_allowed = ['Student [CENTER]']

    def test_list(self):
        u = UserFactory.create(groups=['Student [CENTER]'])
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
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(assignment=a, student=u))
                                for a in (as1 + as2)],
                               resp.context['assignment_list_open'])
        # Add few old assignments from current semester with expired deadline
        deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                       - datetime.timedelta(days=1))
        as_olds = AssignmentFactory.create_batch(2, course_offering=co,
                                             deadline_at=deadline_at)
        resp = self.client.get(reverse(self.url_name))
        for a in as1 + as2 + as_olds:
            self.assertContains(resp, a.title)
        for a in as_olds:
            self.assertContains(resp, a.title)
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(assignment=a, student=u))
                                for a in (as1 + as2)],
                               resp.context['assignment_list_open'])
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(assignment=a, student=u)) for a in as_olds],
                                resp.context['assignment_list_archive'])
        # Now add assignment from old semester
        old_s = SemesterFactory.create(year=now_year - 1, type=now_season)
        old_co = CourseOfferingFactory.create(semester=old_s)
        as_past = AssignmentFactory(course_offering=old_co)
        resp = self.client.get(reverse(self.url_name))
        self.assertNotIn(as_past, resp.context['assignment_list_archive'])

    def test_assignments_from_unenrolled_course_offering(self):
        """Move to archive active assignments from course offerings
        which student already leave
        """
        u = UserFactory.create(groups=['Student [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        # Create open co to pass enrollment limit
        co = CourseOfferingFactory.create(semester=s, is_open=True)
        as1 = AssignmentFactory.create_batch(2, course_offering=co)
        self.doLogin(u)
        # enroll at course offering, assignments are shown
        EnrollmentFactory.create(student=u, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(2, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # Now unenroll from the course
        form = {'course_offering_pk': co.pk}
        url = reverse('course_offering_unenroll',
                      args=[co.course.slug, co.semester.slug])
        response = self.client.post(url, form)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertEquals(2, len(resp.context['assignment_list_archive']))


class AssignmentTeacherListTests(MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_teacher'
    groups_allowed = ['Teacher [CENTER]']

    def test_group_security(self):
        """Custom logic instead of GroupSecurityCheckMixin.
        Teacher can get 404 if no CO yet"""
        self.assertLoginRedirect(reverse(self.url_name))
        for groups in [[], ['Teacher [CENTER]'], ['Student [CENTER]'],
                       ['Graduate']]:
            user = UserFactory.create(groups=groups)
            self.doLogin(user)
            if any(group in self.groups_allowed for group in groups):
                co = CourseOfferingFactory.create(teachers=[user])
                # Create co for teacher to prevent 404 error
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        self.assertStatusCode(404, self.url_name)

    def test_list(self):
        """Leave this test for group security checks.
        Don't want rewrite it in pytest style
        """
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        # some other teacher's course offering
        co_other = CourseOfferingFactory.create(semester=s)
        AssignmentFactory.create_batch(2, course_offering=co_other)
        self.doLogin(teacher)
        # no course offerings and assignments yet, return 404
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(404, resp.status_code)
        # Create co, assignments and enroll students
        co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student, course_offering=co)
        as1 = AssignmentFactory.create_batch(2, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        # By default we show submissions from last 3 assignments,
        # without grades and with comments
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        # Let's check assignments without comments too
        resp = self.client.get(reverse(self.url_name) + "?comment=nomatter")
        self.assertEquals(6, len(resp.context['student_assignment_list']))
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(student=student,
                                      assignment=assignment))
                                for student in students
                                for assignment in as1],
                               resp.context['student_assignment_list'])
        # Teacher commented on an assignment, now it should show up with appropriate filter
        a = as1[0]
        student = students[0]
        a_s = StudentAssignment.objects.get(student=student, assignment=a)
        AssignmentCommentFactory.create(student_assignment=a_s,
                                        author=teacher)
        resp = self.client.get(reverse(self.url_name) + "?comment=teacher")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        # If student have commented, it should show up due to default filter
        AssignmentCommentFactory.create(student_assignment=a_s,
                                        author=student)
        resp = self.client.get(reverse(self.url_name))
        self.assertSameObjects([a_s], resp.context['student_assignment_list'])
        # if teacher has set a grade, assignment shouldn't show up
        a_s.grade = 3
        a_s.save()
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['student_assignment_list']))


class AssignmentTeacherDetailsTest(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        a = AssignmentFactory.create(course_offering__teachers=[teacher])
        url = reverse('assignment_detail_teacher', args=[a.pk])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Teacher [CENTER]']:
                self.assertEquals(403, self.client.get(url).status_code)
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_details(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
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
        a_s = StudentAssignment.objects.get(student=student, assignment=a)
        resp = self.client.get(url)
        self.assertEquals(a, resp.context['assignment'])
        self.assertSameObjects([a_s], resp.context['a_s_list'])


class ASStudentDetailTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_student', args=[a_s.pk])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(student)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_assignment_contents(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_student', args=[a_s.pk])
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.text)

    def test_teacher_redirect_to_appropriate_link(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_student', args=[a_s.pk])
        self.doLogin(student)
        self.assertEquals(200, self.client.get(url).status_code)
        self.doLogin(teacher)
        expected_url = reverse('a_s_detail_teacher', args=[a_s.pk])
        self.assertEquals(302, self.client.get(url).status_code)
        self.assertRedirects(self.client.get(url), expected_url)

    def test_comment(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Teacher [CENTER]']:
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
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == ['Teacher [CENTER]']:
                resp = self.client.post(url, grade_dict)
                self.assertEquals(403, resp.status_code)
            else:
                self.assertPOSTLoginRedirect(url, grade_dict)
            self.doLogout()

    # def test_assignment_contents(self):
    #     teacher = UserFactory.create(groups=['Teacher [CENTER]'])
    #     student = UserFactory.create(groups=['Student [CENTER]'])
    #     co = CourseOfferingFactory.create(teachers=[teacher])
    #     EnrollmentFactory.create(student=student, course_offering=co)
    #     a = AssignmentFactory.create(course_offering=co)
    #     a_s = (StudentAssignment.objects
    #            .filter(assignment=a, student=student)
    #            .get())
    #     url = reverse('a_s_detail_teacher', args=[a_s.pk])
    #     self.doLogin(teacher)
    #     self.assertContains(self.client.get(url), a.text)

    def test_comment(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co,
                                     grade_max=13)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        grade_dict = {'grading_form': True,
                      'grade': 11}
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(url, grade_dict), url)
        self.assertEqual(11, StudentAssignment.objects.get(pk=a_s.pk).grade)
        resp = self.client.get(url)
        self.assertContains(resp, "value=\"11\"")
        self.assertContains(resp, "/{}".format(13))
        # wrong grading value can't be set
        grade_dict['grade'] = 42
        self.client.post(url, grade_dict)
        self.assertEqual(400, self.client.post(url, grade_dict).status_code)
        self.assertEqual(11, StudentAssignment.objects.get(pk=a_s.pk).grade)

    def test_next_unchecked(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        co_other = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        EnrollmentFactory.create(student=student, course_offering=co_other)
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        a_other = AssignmentFactory.create(course_offering=co_other)
        a_s1 = (StudentAssignment.objects
                .filter(assignment=a1, student=student)
                .get())
        a_s2 = (StudentAssignment.objects
                .filter(assignment=a2, student=student)
                .get())
        a_s_other = (StudentAssignment.objects
                     .filter(assignment=a_other, student=student)
                     .get())
        url1 = reverse('a_s_detail_teacher', args=[a_s1.pk])
        url2 = reverse('a_s_detail_teacher', args=[a_s2.pk])
        self.doLogin(teacher)
        self.assertEqual(None, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(None, self.client.get(url2).context['next_a_s_pk'])
        [AssignmentCommentFactory.create(author=a_s.student,
                                         student_assignment=a_s)
         for a_s in [a_s1, a_s2]]
        self.assertEqual(a_s2.pk, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(a_s1.pk, self.client.get(url2).context['next_a_s_pk'])


class AssignmentCRUDTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = AssignmentFactory.attributes(create=True)
        form.update({'course_offering': co.pk,
                     'attached_file': None})
        url = reverse('assignment_add',
                      args=[co.course.slug, co.semester.slug])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        a = AssignmentFactory.create()
        url = reverse('assignment_edit',
                      args=[co.course.slug, co.semester.slug, a.pk])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        url = reverse('assignment_delete',
                      args=[co.course.slug, co.semester.slug, a.pk])
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()

    def test_create(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        CourseOfferingFactory.create_batch(3, teachers=[teacher])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = AssignmentFactory.attributes(create=True)
        deadline_date = form['deadline_at'].strftime("%Y-%m-%d")
        deadline_time = form['deadline_at'].strftime("%H:%M")
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        form = model_to_dict(a)
        deadline_date = form['deadline_at'].strftime("%Y-%m-%d")
        deadline_time = form['deadline_at'].strftime("%H:%M")
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
        self.assertRedirects(self.client.post(url, form),
                             co.get_absolute_url())
        # Show student assignments without comments
        self.assertContains(self.client.get( list_url + "?status=all"), form['title'])

    def test_delete(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
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
    groups_allowed = ['Teacher [CENTER]']

    def test_redirect(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
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
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
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
        """Test marksheet with empty assignments list"""
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        co1 = CourseOfferingFactory.create(teachers=[teacher])
        co2 = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student, course_offering=co1)
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
            enrollment = Enrollment.objects.get(student=student,
                                        course_offering=co1)
            field = 'final_grade_{}'.format(enrollment.pk)
            self.assertIn(field, resp.context['form'].fields)
        for co in [co1, co2]:
            url = reverse('markssheet_teacher',
                          args=[co.course.slug,
                                co.semester.year,
                                co.semester.type])
            self.assertContains(resp, url)

    def test_nonempty_markssheet(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
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
                a_s = StudentAssignment.objects.get(student=student,
                                                    assignment=as_)
                a_s_url = reverse('a_s_detail_teacher', args=[a_s.pk])
                self.assertContains(resp, a_s_url)
        for as_ in as_offline:
            self.assertContains(resp, as_.title)
            for student in students:
                a_s = StudentAssignment.objects.get(student=student,
                                                    assignment=as_)
                self.assertIn('a_s_{}'.format(a_s.pk),
                              resp.context['form'].fields)

    def test_total_score(self):
        """Calculate total score by assignments for course offering"""
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        student = UserFactory.create(groups=['Student [CENTER]'])
        EnrollmentFactory.create(student=student, course_offering=co)
        as_cnt = 2
        assignments = AssignmentFactory.create_batch(as_cnt, course_offering=co)
        # AssignmentFactory implicitly create StudentAssignment instances
        # with empty grade value.
        default_grade = 10
        for assignment in assignments:
            a_s = StudentAssignment.objects.get(student=student,
                                                assignment=assignment)
            a_s.grade = default_grade
            a_s.save()
        expected_total_score = as_cnt * default_grade
        url = reverse('markssheet_teacher', args=[co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
        self.doLogin(teacher)
        resp = self.client.get(url)
        head_student = next(iter(resp.context['students'].items()))
        self.assertEquals(head_student[1]["total"], expected_total_score)

    def test_save_markssheet(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(2, groups=['Student [CENTER]'])
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
        pairs = zip([StudentAssignment.objects.get(student=student, assignment=a)
                     for student in students
                     for a in [a1, a2]],
            [2, 3, 4, 5])
        for submission, grade in pairs:
            enrollment = Enrollment.objects.get(student=submission.student,
                                                course_offering=co)
            form['a_s_{}'.format(submission.pk)] = grade
            field = 'final_grade_{}'.format(enrollment.pk)
            form[field] = 'good'
        self.assertRedirects(self.client.post(url, form), url)
        for a_s, grade in pairs:
            self.assertEqual(grade, (StudentAssignment.objects
                                     .get(pk=a_s.pk)
                                     .grade))
        for student in students:
            self.assertEqual('good', (Enrollment.objects
                                      .get(student=student,
                                           course_offering=co)
                                      .grade))

    def test_import_stepic(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        student = UserFactory.create(groups=['Student [CENTER]'])
        EnrollmentFactory.create(student=student, course_offering=co)
        assignments = AssignmentFactory.create_batch(3, course_offering=co)
        # for assignment in assignments:
        #     a_s = StudentAssignment.objects.get(student=student,
        #                                         assignment=assignment)
        # Import grades allowed only for particular course offering
        form_fields = {'assignment': assignments[0].pk}
        form = MarksSheetTeacherImportGradesForm(form_fields,
                                                 c_slug=co.course.slug)
        self.assertFalse(form.is_valid())
        self.assertListEqual(list(form.errors.keys()), ['csvfile'])
        # Teachers can import grades only for own CO
        teacher2 = UserFactory.create(groups=['Teacher [CENTER]'])
        self.doLogin(teacher2)
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertEqual(resp.status_code, 404)
        # Wrong assignment id
        self.doLogin(teacher)
        form = MarksSheetTeacherImportGradesForm(
            {'assignment': max((a.pk for a in assignments)) + 1},
            c_slug=co.course.slug)
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
        # Wrong course offering slug
        form = MarksSheetTeacherImportGradesForm(form_fields,
                                                 c_slug='THIS_SLUG_CANT_EXIST')
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
        # CO not found
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk + 1])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertEqual(resp.status_code, 404)
        # Check redirects
        redirect_url = reverse('markssheet_teacher',
                               args=[co.course.slug, co.semester.year, co.semester.type])
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertRedirects(resp, redirect_url)
        self.assertIn('messages', resp.cookies)
        # TODO: provide testing with request.FILES. Move it to test_utils...
    # TODO: write test for user search by stepic id


class MarksSheetCSVTest(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student = UserFactory.create(groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        EnrollmentFactory.create(student=student, course_offering=co)
        url = reverse('markssheet_teacher_csv',
                      args=[co.course.slug, co.semester.slug])
        self.assertLoginRedirect(url)
        for groups in [[], ['Student [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
        self.doLogin(UserFactory.create(groups=['Teacher [CENTER]']))
        self.assertEquals(404, self.client.get(url).status_code)
        self.doLogin(student)
        self.assertLoginRedirect(url)
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_csv(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        student1, student2 = UserFactory.create_batch(2, groups=['Student [CENTER]'])
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
            a_s = StudentAssignment.objects.get(student=s, assignment=a)
            a_s.grade = grade
            a_s.save()
        self.doLogin(teacher)
        data = [row for row in unicodecsv.reader(self.client.get(url)) if row]
        self.assertEquals(3, len(data))
        self.assertIn(a1.title, data[0])
        row_last_names = [row[0] for row in data]
        for a, s, grade in combos:
            row = row_last_names.index(s.last_name)
            col = data[0].index(a.title)
            self.assertEquals(grade, int(data[row][col]))


class NonCourseEventDetailTests(MyUtilitiesMixin, TestCase):
    def basic_test(self):
        evt = NonCourseEventFactory.create()
        url = cc.get_absolute_url()
        resp = self.client.get(url)
        self.assertContains(evt.name, resp)
        self.assertContains(evt.venue.get_absolute_url(), resp)


# Ok, py.test starts here

@pytest.mark.django_db
class TestCompletedCourseOfferingBehaviour(object):
    def test_security_assignmentstudent_detail(self, client,
                                               teacher_center_factory,
                                               student_factory):
        """Students can't see assignments from completed course, which they failed"""
        teacher = teacher_center_factory()
        student = student_factory()
        past_year = datetime.datetime.now().year - 3
        past_semester = SemesterFactory.create(year=past_year)
        co = CourseOfferingFactory(teachers=[teacher], semester=past_semester,
                                   is_completed=True)
        enrollment = EnrollmentFactory(student=student, course_offering=co,
                                       grade=GRADES.unsatisfactory)
        a = AssignmentFactory(course_offering=co)
        a_s = StudentAssignment.objects.get(student=student, assignment=a)
        url = reverse('a_s_detail_student', args=[a_s.pk])
        client.login(student)
        response = client.get(url)
        assert response.status_code == 403
        # Teacher still can view student assignment
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        client.login(teacher)
        response = client.get(url)
        assert response.status_code == 200

    def test_security_courseoffering_detail(self, client,
                                            teacher_center_factory,
                                            student_factory):
        """Students can't see news from completed course, which they failed"""
        teacher = teacher_center_factory()
        student = student_factory()
        past_year = datetime.datetime.now().year - 3
        past_semester = SemesterFactory.create(year=past_year)
        co = CourseOfferingFactory(teachers=[teacher], semester=past_semester,
                                   is_completed=True)
        enrollment = EnrollmentFactory(student=student, course_offering=co,
                                       grade=GRADES.unsatisfactory)
        a = AssignmentFactory(course_offering=co)
        client.login(student)
        url = reverse('course_offering_detail',
                      kwargs={"course_slug": co.course.slug,
                              "semester_slug": past_semester.slug})
        response = client.get(url)
        assert response.context["is_failed_completed_course"]
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find(text=_("News")) is None
        # Change student co mark
        enrollment.grade = GRADES.excellent
        enrollment.save()
        response = client.get(url)
        assert not response.context["is_failed_completed_course"]
        # Change course offering state to not completed
        co.is_completed = False
        co.save()
        response = client.get(url)
        assert not response.context["is_failed_completed_course"]




class CourseOfferingEnrollmentTests(MyUtilitiesMixin, TestCase):

    @unittest.skip('not implemented')
    def test_enrollment_for_club_students(self):
        """ Club Student can enroll only on open courses """
        pass

    def test_unenrollment(self):
        s = UserFactory.create(groups=['Student [CENTER]'])
        today = timezone.now()
        current_semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(semester=current_semester)
        as_ = AssignmentFactory.create_batch(3, course_offering=co)
        form = {'course_offering_pk': co.pk}
        url = reverse('course_offering_unenroll',
                      args=[co.course.slug, co.semester.slug])
        self.doLogin(s)
        # Enrollment already closed
        current_semester.enroll_before = (today - datetime.timedelta(days=1)).date()
        current_semester.save()
        response = self.client.post(reverse('course_offering_enroll',
                                 args=[co.course.slug, co.semester.slug]),
                         form)
        assert response.status_code == 403
        current_semester.enroll_before = today.date()
        current_semester.save()
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
        a_ss = (StudentAssignment.objects
                .filter(student=s,
                        assignment__course_offering=co))
        self.assertEquals(3, len(a_ss))
        self.client.post(reverse('course_offering_enroll',
                                 args=[co.course.slug, co.semester.slug]),
                         form)
        url += "?back=course_list_student"
        self.assertRedirects(self.client.post(url, form),
                             reverse('course_list_student'))
        self.assertSameObjects(a_ss, (StudentAssignment.objects
                                      .filter(student=s,
                                              assignment__course_offering=co)))


@pytest.mark.django_db
def test_enrollment(client):
    from django.utils import dateformat
    student = UserFactory.create(groups=['Student [CENTER]'])
    client.login(student)
    today = timezone.now()
    current_semester = SemesterFactory.create_current()
    current_semester.enroll_before = today.date()
    current_semester.save()
    co = CourseOfferingFactory.create(semester=current_semester)
    url = reverse('course_offering_enroll',
                  args=[co.course.slug, co.semester.slug])
    form = {'course_offering_pk': co.pk}
    response = client.post(url, form)
    assert response.status_code == 302
    # FIXME: Find how to assert redirects with pytest and Django
    # assert response.url == client.request.get_absolute_uri(co.get_absolute_url())
    assert 1 == (Enrollment.objects
                      .filter(student=student, course_offering=co)
                      .count())
    as_ = AssignmentFactory.create_batch(3, course_offering=co)
    assert set((student.pk, a.pk) for a in as_) == set(StudentAssignment.objects
                          .filter(student=student)
                          .values_list('student', 'assignment'))
    co_other = CourseOfferingFactory.create(semester=current_semester)
    form.update({'back': 'course_list_student'})
    url = reverse('course_offering_enroll',
                  args=[co_other.course.slug, co_other.semester.slug])
    response = client.post(url, form)
    assert response.status_code == 302
    # assert response.url == reverse('course_list_student')
    # Try to enroll to old CO
    old_semester = SemesterFactory.create(year=2010)
    old_co = CourseOfferingFactory.create(semester=old_semester)
    form = {'course_offering_pk': old_co.pk}
    url = reverse('course_offering_enroll',
                  args=[old_co.course.slug, old_co.semester.slug])
    assert client.post(url, form).status_code == 403

# TODO: test CourseOffering edit-description page. returned more than one CourseOffering error if we have CO for kzn and spb


@pytest.mark.django_db
def test_assignment_contents(client):
    teacher = UserFactory.create(groups=['Teacher [CENTER]'])
    student = UserFactory.create(groups=['Student [CENTER]'])
    # XXX: Unexpected Segfault when running pytest.
    # Move this test from ASTeacherDetailTests cls.
    # No idea why it's happening on login action
    # if assignment `notify_teachers` field not specified.
    # Problem can be related to pytest, django tests or factory-boy
    co = CourseOfferingFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course_offering=co)
    a = AssignmentFactory.create(course_offering=co)
    a_s = (StudentAssignment.objects
           .filter(assignment=a, student=student)
           .get())
    url = reverse('a_s_detail_teacher', args=[a_s.pk])
    client.login(teacher)
    assert smart_bytes(a.text) in client.get(url).content


@pytest.mark.django_db
def test_studentassignment_last_commented_from(client,
                                               student_center_factory,
                                               teacher_center_factory):
    teacher = teacher_center_factory.create()
    student = student_center_factory.create()
    now_year, now_season = get_current_semester_pair()
    s = SemesterFactory.create(year=now_year, type=now_season)
    co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
    EnrollmentFactory.create(student=student, course_offering=co)
    assignment = AssignmentFactory.create(course_offering=co)
    sa = StudentAssignment.objects.get(assignment=assignment)
    # Nobody comments yet
    assert sa.last_comment_from == StudentAssignment.LAST_COMMENT_NOBODY
    AssignmentCommentFactory.create(student_assignment=sa, author=student)
    assert sa.last_comment_from == StudentAssignment.LAST_COMMENT_STUDENT
    AssignmentCommentFactory.create(student_assignment=sa, author=teacher)
    assert sa.last_comment_from == StudentAssignment.LAST_COMMENT_TEACHER


@pytest.mark.django_db
def test_gradebook_recalculate_grading_type(client,
                                            student_center_factory,
                                            teacher_center_factory):
    teacher = teacher_center_factory.create()
    students = student_center_factory.create_batch(2)
    s = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
    assert co.grading_type == GRADING_TYPES.default
    assignments = AssignmentFactory.create_batch(2,
                                                 course_offering=co,
                                                 is_online=True)
    client.login(teacher)
    url = reverse('markssheet_teacher', args=[co.course.slug,
                                              co.semester.year,
                                              co.semester.type])
    form = {}
    for s in students:
        enrollment = EnrollmentFactory.create(student=s, course_offering=co)
        field = 'final_grade_{}'.format(enrollment.pk)
        form[field] = GRADES.good
    # Save empty form first
    response = client.post(url, {}, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.default
    # Update final grades, still should be `default`
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.default
    enrollment.refresh_from_db()
    assert enrollment.grade == GRADES.good
    student = students[0]
    user_detail_url = reverse('user_detail', args=[student.pk])
    # Now we should get `binary` type after all final grades
    # will be equal `unsatisfactory`
    for key in form:
        form[key] = GRADES.unsatisfactory
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.binary
    response = client.get(user_detail_url)
    assert smart_bytes("(enrollment|unsatisfactory)") in response.content
    # Update random submission grade, grading_type shouldn't change
    submission = StudentAssignment.objects.get(student=student,
                                               assignment=assignments[0])
    form = {
        'a_s_{}'.format(submission.pk): 2  # random valid grade
    }
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.binary
    # Manually set default grading type and check that grade repr changed
    co.grading_type = GRADING_TYPES.default
    co.save()
    response = client.get(user_detail_url)
    assert smart_bytes("(enrollment|unsatisfactory)") not in response.content
    assert smart_bytes("(unsatisfactory)") in response.content
