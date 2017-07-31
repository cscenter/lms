# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import os
import unittest

import pytest
import unicodecsv
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import smart_text, smart_bytes
from testfixtures import LogCapture

from core.utils import city_aware_reverse
from learning.forms import MarksSheetTeacherImportGradesForm, CourseClassForm
from learning.settings import GRADES, GRADING_TYPES, \
    STUDENT_STATUS
from users.factories import TeacherCenterFactory, StudentFactory, \
    StudentCenterFactory
from .mixins import *
from ..factories import *


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

    @pytest.mark.skip("Buggy in the end of the month. WTF!")
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


# TODO: add test: kzn courses not shown on center site and spb on kzn
# TODO: add test: summer courses not shown on club site on main page


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
        co1, co2 = CourseOfferingFactory.create_batch(
            2, course=c, city=settings.DEFAULT_CITY_CODE)
        response = self.client.get(c.get_absolute_url())
        self.assertContains(response, c.name)
        self.assertContains(response, c.description)
        # Course offerings not repeated, used set to compare
        assert {c.pk for c in response.context['offerings']} == {co1.pk, co2.pk}
        co2.city_id = "kzn"
        co2.save()
        response = self.client.get(c.get_absolute_url())
        if settings.SITE_ID == settings.CENTER_SITE_ID:
            assert {c.pk for c in response.context['offerings']} == {co1.pk}


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
        assert 200 == self.client.get(co.get_absolute_url()).status_code
        url = city_aware_reverse('course_offering_detail', kwargs={
            "course_slug": "space-odyssey",
            "semester_slug": "2010",
            "city_code": ""
        })
        # Can't parse `semester_slug`
        self.assertEqual(400, self.client.get(url).status_code)

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
        next_day = now() + datetime.timedelta(days=1)
        co = CourseOfferingFactory.create(teachers=[teacher],
                                          completed_at=next_day)
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
        url = co.get_update_description_url()
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
        self.url = self.co.get_create_news_url()
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
        self.url = self.con.get_update_url()
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
        self.url = self.con.get_delete_url()

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
                                              city="kzn")
        resp = self.client.get(reverse('course_list'))
        # Really stupid test, we filter summer courses on /courses/ page
        if current_semester.type != Semester.TYPES.summer:
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
                                          city="kzn")
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
        url = co.get_create_class_url()
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
        url = co.get_create_class_url()
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
        url = co.get_create_class_url()
        # should save with course_offering = co
        response = self.client.post(url, form)
        expected_url = co.get_create_class_url()
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
        url = cc.get_update_url()
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
        url = cc.get_update_url()
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
        expected_url = co.get_create_class_url()
        self.assertRedirects(self.client.post(url, form), expected_url)

    def test_delete(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course_offering=co)
        url = cc.get_delete_url()
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
        base_url = cc.get_update_url()
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
        url = cc.get_update_url()
        resp = self.client.get(url)
        self.assertContains(resp, cca1.get_delete_url())
        self.assertContains(resp, cca1.material_file_name)
        self.assertContains(resp, cca2.get_delete_url())
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
        url = cc.get_update_url()
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
        url = cca_to_delete.get_delete_url()
        # check security just in case
        self.doLogout()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, {})
        self.doLogin(teacher)
        self.assertContains(self.client.get(url),
                            cca_to_delete.material_file_name)
        self.assertRedirects(self.client.post(url),
                             cc.get_update_url())
        response = self.client.get(cc.get_absolute_url())
        spans = (BeautifulSoup(response.content, "html.parser")
                 .find_all('span', class_='assignment-attachment'))
        self.assertEquals(1, len(spans))
        self.assertRegexpMatches(spans[0].a.contents[0].strip(),
                                 "attachment1(_[0-9a-zA-Z]+)?.txt")
        self.assertFalse(os.path.isfile(cca_files[1]))


class AssignmentTeacherListTests(MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_teacher'
    groups_allowed = ['Teacher [CENTER]']

    def test_group_security(self):
        """Custom logic instead of GroupSecurityCheckMixin.
        Teacher can get 302 if no CO yet"""
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
        self.assertStatusCode(302, self.url_name)

    def test_list(self):
        # Default filter for grade - `no_grade`
        TEACHER_ASSIGNMENTS_PAGE = reverse(self.url_name)
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        # some other teacher's course offering
        co_other = CourseOfferingFactory.create(semester=s)
        AssignmentFactory.create_batch(2, course_offering=co_other)
        self.doLogin(teacher)
        # no course offerings yet, return 302
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE)
        self.assertEquals(302, resp.status_code)
        # Create co, assignments and enroll students
        co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
        for student1 in students:
            EnrollmentFactory.create(student=student1, course_offering=co)
        assignment = AssignmentFactory.create(course_offering=co)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE)
        # TODO: add wrong term type and check redirect.
        # By default we show all submissions without grades
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        # Show submissions without comments
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        # TODO: add test which assignment selected by default.
        sas = ((StudentAssignment.objects.get(student=student,
                                              assignment=assignment))
               for student in students)
        self.assertSameObjects(sas, resp.context['student_assignment_list'])
        # Let's check assignments with last comment from student only
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        # Teacher commented on student1 assignment
        student1, student2, student3 = students
        sa1 = StudentAssignment.objects.get(student=student1,
                                            assignment=assignment)
        sa2 = StudentAssignment.objects.get(student=student2,
                                            assignment=assignment)
        AssignmentCommentFactory.create(student_assignment=sa1, author=teacher)
        assert sa1.last_comment_from == sa1.LAST_COMMENT_TEACHER
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(reverse(self.url_name) + "?comment=teacher")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(2, len(resp.context['student_assignment_list']))
        # Student2 commented on assignment
        AssignmentCommentFactory.create_batch(2, student_assignment=sa2,
                                              author=student2)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        self.assertSameObjects([sa2], resp.context['student_assignment_list'])
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        # Teacher answered on the student2 assignment
        AssignmentCommentFactory.create(student_assignment=sa2, author=teacher)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEquals(2, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        # Student 3 add comment on assignment
        sa3 = StudentAssignment.objects.get(student=student3,
                                            assignment=assignment)
        AssignmentCommentFactory.create_batch(3, student_assignment=sa3,
                                              author=student3)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEquals(2, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        # teacher has set a grade
        sa3.grade = 3
        sa3.save()
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&grades=no")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&grades=all")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        sa3.refresh_from_db()
        sa1.grade = 3
        sa1.save()
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&grades=yes")
        self.assertEquals(1, len(resp.context['student_assignment_list']))


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
        # Change student to graduate, make sure they have access to HW
        student.groups.clear()
        student.groups.add(PARTICIPANT_GROUPS.GRADUATE_CENTER)
        student.save()
        self.assertEquals(200, self.client.get(url).status_code)

    def test_failed_course(self):
        """
        Make sure student has access only to assignments which he passed if
        he completed course with unsatisfactory grade
        """
        teacher = TeacherCenterFactory()
        student = StudentFactory()
        past_year = datetime.datetime.now().year - 3
        past_semester = SemesterFactory.create(year=past_year)
        co = CourseOfferingFactory(teachers=[teacher], semester=past_semester)
        enrollment = EnrollmentFactory(student=student, course_offering=co,
                                       grade=GRADES.unsatisfactory)
        a = AssignmentFactory(course_offering=co)
        s_a = StudentAssignment.objects.get(student=student, assignment=a)
        assert s_a.grade is None
        self.doLogin(student)
        url = reverse("a_s_detail_student", args=[s_a.pk])
        response = self.client.get(url)
        assert response.status_code == 403
        # Student discussed the assignment, so has access
        ac = AssignmentCommentFactory.create(student_assignment=s_a,
                                             author=student)
        response = self.client.get(url)
        co.refresh_from_db()
        assert co.failed_by_student(student)
        # Course completed, but not failed, user can see all assignments
        ac.delete()
        enrollment.grade = GRADES.good
        enrollment.save()
        response = self.client.get(url)
        assert not co.failed_by_student(student)
        assert response.status_code == 200
        # The same behavior should be for expelled student
        student.status = STUDENT_STATUS.expelled
        student.save()
        self.doLogin(student)
        response = self.client.get(url)
        assert response.status_code == 200
        enrollment.grade = GRADES.unsatisfactory
        enrollment.save()
        response = self.client.get(url)
        assert response.status_code == 403
        ac = AssignmentCommentFactory.create(student_assignment=s_a,
                                             author=student)
        response = self.client.get(url)
        assert response.status_code == 200
        # Ok, next case - completed course failed, no comments but has grade
        ac.delete()
        s_a.grade = 1
        s_a.save()
        response = self.client.get(url)
        assert response.status_code == 200
        # The same if student not expelled
        student.status = STUDENT_STATUS.will_graduate
        student.save()
        self.doLogin(student)
        response = self.client.get(url)
        assert response.status_code == 200

    def test_assignment_contents(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(semester=semester)
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
        semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(teachers=[teacher], semester=semester)
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
        url = co.get_create_assignment_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        a = AssignmentFactory.create()
        url = a.get_update_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        for groups in [[], ['Student [CENTER]'], ['Teacher [CENTER]']]:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        url = a.get_delete_url()
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
        deadline_date = form['deadline_at'].strftime("%d.%m.%Y")
        deadline_time = form['deadline_at'].strftime("%H:%M")
        form.update({'course_offering': co.pk,
                     'attached_file': None,
                     'deadline_at_0': deadline_date,
                     'deadline_at_1': deadline_time})
        url = co.get_create_assignment_url()
        self.doLogin(teacher)
        self.client.post(url, form)
        assert Assignment.objects.count() == 1

    def test_update(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        form = model_to_dict(a)
        deadline_date = form['deadline_at'].strftime("%d.%m.%Y")
        deadline_time = form['deadline_at'].strftime("%H:%M")
        form.update({'title': a.title + " foo42bar",
                     'course_offering': co.pk,
                     'attached_file': None,
                     'deadline_at_0': deadline_date,
                     'deadline_at_1': deadline_time})
        url = a.get_update_url()
        list_url = reverse('assignment_list_teacher')
        self.doLogin(teacher)
        self.assertNotContains(self.client.get(list_url), form['title'])
        self.assertRedirects(self.client.post(url, form),
                             reverse("assignment_detail_teacher", args=[a.pk]))
        # Show student assignments without comments
        self.assertContains(self.client.get( list_url + "?status=all"), form['title'])

    def test_delete(self):
        teacher = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a = AssignmentFactory.create(course_offering=co)
        url = a.get_delete_url()
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
                         args=[co.get_city(),
                               co.course.slug,
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
                             args=[co.get_city(),
                                   co.course.slug,
                                   co.semester.year,
                                   co.semester.type])
            self.assertContains(self.client.get(url), co_url)

    # TODO: test redirect to gradebook for teachers if only 1 course in current term


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
        url = reverse('markssheet_teacher', args=[co1.get_city(),
                                                  co1.course.slug,
                                                  co1.semester.year,
                                                  co1.semester.type])
        self.doLogin(teacher)
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name, 1)
            enrollment = Enrollment.active.get(student=student,
                                        course_offering=co1)
            field = 'final_grade_{}'.format(enrollment.pk)
            self.assertIn(field, resp.context['form'].fields)
        for co in [co1, co2]:
            url = reverse('markssheet_teacher',
                          args=[co.get_city(),
                                co.course.slug,
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
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
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
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
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
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
        self.doLogin(teacher)
        form = {}
        pairs = zip([StudentAssignment.objects.get(student=student, assignment=a)
                     for student in students
                     for a in [a1, a2]],
            [2, 3, 4, 5])
        for submission, grade in pairs:
            enrollment = Enrollment.active.get(student=submission.student,
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
            self.assertEqual('good', (Enrollment.active
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
                                                 course_id=co.course.pk)
        self.assertFalse(form.is_valid())
        self.assertListEqual(list(form.errors.keys()), ['csv_file'])
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
            course_id=co.course.id)
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
        # Wrong course offering id
        form = MarksSheetTeacherImportGradesForm(form_fields, course_id=-1)
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
        # CO not found
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk + 1])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertEqual(resp.status_code, 404)
        # Check redirects
        redirect_url = reverse('markssheet_teacher',
                               args=[co.get_city(),
                                     co.course.slug,
                                     co.semester.year,
                                     co.semester.type])
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
                      args=[co.get_city(), co.course.slug, co.semester.slug])
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
                      args=[co.get_city(), co.course.slug, co.semester.slug])
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

# TODO: test CourseOffering edit-description page. returned more than one CourseOffering error if we have CO for kzn and spb


@pytest.mark.django_db
def test_gradebook_recalculate_grading_type(client):
    teacher = TeacherCenterFactory.create()
    students = StudentCenterFactory.create_batch(2)
    s = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
    assert co.grading_type == GRADING_TYPES.default
    assignments = AssignmentFactory.create_batch(2,
                                                 course_offering=co,
                                                 is_online=True)
    client.login(teacher)
    url = reverse('markssheet_teacher', args=[co.get_city(),
                                              co.course.slug,
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
    student = students[0]
    user_detail_url = reverse('user_detail', args=[student.pk])
    # Now we should get `binary` type after all final grades
    # will be equal `pass`
    for key in form:
        form[key] = getattr(GRADES, 'pass')
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.binary
    response = client.get(user_detail_url)
    assert smart_bytes("/enrollment|pass/") in response.content
    assert smart_bytes("/satisfactory/") not in response.content
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
    assert smart_bytes("/enrollment|pass/") not in response.content
    assert smart_bytes("/satisfactory/") in response.content


@pytest.mark.django_db
def test_course_class_form(client, curator, settings):
    """Test form availability based on `is_completed` value"""
    # XXX: Date widget depends on locale, don't know exactly why
    settings.LANGUAGE_CODE = 'ru'
    teacher = TeacherCenterFactory()
    semester = SemesterFactory.create_current()
    co = CourseOfferingFactory(semester=semester, teachers=[teacher])
    course_class_add_url = co.get_create_class_url()
    response = client.get(course_class_add_url)
    assert response.status_code == 302
    client.login(teacher)
    response = client.get(course_class_add_url)
    assert response.status_code == 200
    # Check form visible
    assert smart_bytes("submit-id-save") in response.content
    # Course completed, form invisible for teacher
    co.completed_at = now().date()
    co.save()
    response = client.get(course_class_add_url)
    assert smart_bytes("Курс завершён") in response.content
    client.login(curator)
    response = client.get(course_class_add_url)
    assert smart_bytes("Курс завершён") not in response.content
    # Try to send form directly by teacher
    client.login(teacher)
    form = {}
    response = client.post(course_class_add_url, form, follow=True)
    assert response.status_code == 403
    # Check we can post form if course is active
    co.completed_at = now().date() + datetime.timedelta(days=1)
    co.save()
    next_day = now() + datetime.timedelta(days=1)
    venue = VenueFactory()
    date_format = CourseClassForm.base_fields['date'].widget.format
    form = {
        "type": "lecture",
        "venue": venue.pk,
        "name": "Test class",
        "date": next_day.strftime(date_format),
        "starts_at": "17:20",
        "ends_at": "18:50"
    }
    response = client.post(course_class_add_url, form, follow=True)
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    # FIXME: добавить тест на is_form_available и посмотреть, можно ли удалить эту часть, по-моему это лишняя логика


# TODO: Написать тест, который проверяет, что по-умолчанию в форму
# редактирования описания ПРОЧТЕНИЯ подставляется описание из курса. И описание прочтения, если оно уже есть.

# TODO: test redirects on course offering page if tab exists but user has no access