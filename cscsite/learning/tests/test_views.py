# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import logging
import os
import unittest

import pytest
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import smart_text, smart_bytes
from testfixtures import LogCapture

from core.utils import city_aware_reverse
from learning.forms import CourseClassForm
from learning.settings import GRADES, STUDENT_STATUS
from learning.tests.utils import check_group_security
from users.factories import TeacherCenterFactory, StudentFactory, \
    StudentCenterFactory
from .mixins import *
from ..factories import *




# TODO: Написать тест, который проверяет, что по-умолчанию в форму
# редактирования описания ПРОЧТЕНИЯ подставляется описание из курса. И описание прочтения, если оно уже есть.

# TODO: test redirects on course offering page if tab exists but user has no access





class GroupSecurityCheckMixin(MyUtilitiesMixin):
    def test_group_security(self):
        """
        Checks if only users in groups listed in self.groups_allowed can
        access the page which url is stored in self.url_name.
        Also checks that curator can access any page
        """
        self.assertTrue(self.groups_allowed is not None)
        self.assertTrue(self.url_name is not None)
        self.assertLoginRedirect(reverse(self.url_name))
        all_test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
            [PARTICIPANT_GROUPS.GRADUATE_CENTER]
        ]
        for groups in all_test_groups:
            self.doLogin(UserFactory.create(groups=groups, city_id='spb'))
            if any(group in self.groups_allowed for group in groups):
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True, city_id='spb'))
        self.assertStatusCode(200, self.url_name)


class TimetableTeacherTests(GroupSecurityCheckMixin,
                            MyUtilitiesMixin, TestCase):
    url_name = 'timetable_teacher'
    groups_allowed = [PARTICIPANT_GROUPS.TEACHER_CENTER]

    @pytest.mark.skip("Buggy in the end of the month. WTF!")
    def test_teacher_timetable(self):
        teacher = TeacherCenterFactory()
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
    groups_allowed = [PARTICIPANT_GROUPS.STUDENT_CENTER]

    def test_student_timetable(self):
        student = StudentCenterFactory()
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
        u = TeacherCenterFactory()
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
    groups_allowed = [PARTICIPANT_GROUPS.TEACHER_CENTER]


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
        all_test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
            [PARTICIPANT_GROUPS.GRADUATE_CENTER]
        ]
        for groups in all_test_groups:
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
        student = StudentCenterFactory()
        teacher = TeacherCenterFactory()
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
        student = StudentCenterFactory()
        teacher = TeacherCenterFactory()
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
        self.assertContains(self.client.get(url), a_s.get_student_url())
        a_s.delete()
        with LogCapture(level=logging.INFO) as l:
            self.assertEqual(200, self.client.get(url).status_code)
            l.check(('learning.views.course_offering',
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
        teacher = TeacherCenterFactory()
        teacher_other = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        url = co.get_update_url()
        self.assertLoginRedirect(url)
        self.doLogin(teacher_other)
        self.assertLoginRedirect(url)
        self.doLogout()
        self.doLogin(teacher)
        self.assertStatusCode(200, url, make_reverse=False)


class CourseOfferingNewsCreateTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = TeacherCenterFactory()
        self.teacher_other = TeacherCenterFactory()
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
        co_url = self.co.get_url_for_tab("news")
        self.doLogin(self.teacher)
        self.assertRedirects(
            self.client.post(self.url, self.n_dict), co_url)
        resp = self.client.get(co_url)
        self.assertContains(resp, self.n_dict['text'])
        con = resp.context['course_offering'].courseofferingnews_set.all()[0]
        self.assertEqual(con.author, self.teacher)


class CourseOfferingNewsUpdateTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = TeacherCenterFactory()
        self.teacher_other = TeacherCenterFactory()
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
        co_url = self.co.get_url_for_tab("news")
        self.assertRedirects(
            self.client.post(self.url, self.con_dict), co_url)
        self.assertContains(self.client.get(co_url), self.con_dict['text'])


class CourseOfferingNewsDeleteTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = TeacherCenterFactory()
        self.teacher_other = TeacherCenterFactory()
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
        s = StudentCenterFactory(city_id=settings.DEFAULT_CITY_CODE)
        self.doLogin(s)
        current_semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(semester=current_semester,
                                          city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseOfferingFactory.create(semester=current_semester,
                                              city="kzn")
        response = self.client.get(reverse('course_list_student'))
        self.assertEqual(len(response.context['course_list_available']), 1)


class CourseClassDetailTests(MyUtilitiesMixin, TestCase):
    def test_is_actual_teacher(self):
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = CourseClassFactory.attributes(create=True)
        form.update({'venue': VenueFactory.create().pk})
        url = co.get_create_class_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)

    def test_create(self):
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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
        teacher = TeacherCenterFactory()
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


class ASStudentDetailTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        now_year, now_season = get_current_semester_pair()
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
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
        url = s_a.get_student_url()
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
        student = StudentCenterFactory()
        semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(semester=semester)
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.text)

    def test_teacher_redirect_to_appropriate_link(self):
        student = StudentCenterFactory()
        teacher = TeacherCenterFactory()
        semester = SemesterFactory.create_current()
        co = CourseOfferingFactory.create(teachers=[teacher], semester=semester)
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        self.assertEquals(200, self.client.get(url).status_code)
        self.doLogin(teacher)
        expected_url = a_s.get_teacher_url()
        self.assertEquals(302, self.client.get(url).status_code)
        self.assertRedirects(self.client.get(url), expected_url)

    def test_comment(self):
        student = StudentCenterFactory()
        co = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
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
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_teacher_url()
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [PARTICIPANT_GROUPS.TEACHER_CENTER]:
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
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER]
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [PARTICIPANT_GROUPS.TEACHER_CENTER]:
                resp = self.client.post(url, grade_dict)
                self.assertEquals(403, resp.status_code)
            else:
                self.assertPOSTLoginRedirect(url, grade_dict)
            self.doLogout()

    # def test_assignment_contents(self):
    #     teacher = TeacherCenterFactory()
    #     student = StudentCenterFactory()
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
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_teacher_url()
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
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course_offering=co)
        a = AssignmentFactory.create(course_offering=co,
                                     grade_max=13)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_teacher_url()
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
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
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
        url1 = a_s1.get_teacher_url()
        url2 = a_s2.get_teacher_url()
        self.doLogin(teacher)
        self.assertEqual(None, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(None, self.client.get(url2).context['next_a_s_pk'])
        [AssignmentCommentFactory.create(author=a_s.student,
                                         student_assignment=a_s)
         for a_s in [a_s1, a_s2]]
        self.assertEqual(a_s2.pk, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(a_s1.pk, self.client.get(url2).context['next_a_s_pk'])


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


@pytest.mark.django_db
def test_student_courses_list(client, settings):
    url = reverse('course_list_student')
    check_group_security(client, settings,
                         groups_allowed=[PARTICIPANT_GROUPS.STUDENT_CENTER],
                         url=url)
    student = StudentCenterFactory(city_id=settings.DEFAULT_CITY_CODE)
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context['course_list_available']) == 0
    assert len(response.context['enrollments_ongoing']) == 0
    assert len(response.context['enrollments_archive']) == 0
    now_year, now_season = get_current_semester_pair()
    s = SemesterFactory.create(year=now_year, type=now_season)
    cos = CourseOfferingFactory.create_batch(4, semester=s,
                                             city_id=settings.DEFAULT_CITY_CODE)
    cos_available = cos[:2]
    cos_enrolled = cos[2:]
    enrollments_ongoing = []
    enrollments_archive = []
    cos_archived = CourseOfferingFactory.create_batch(3,
        semester__year=now_year - 1)
    for co in cos_enrolled:
        enrollments_ongoing.append(
            EnrollmentFactory.create(student=student, course_offering=co))
    for co in cos_archived:
        enrollments_archive.append(
            EnrollmentFactory.create(student=student, course_offering=co))
    response = client.get(url)
    context = response.context
    assert len(enrollments_ongoing) == len(context['enrollments_ongoing'])
    assert set(enrollments_ongoing) == set(context['enrollments_ongoing'])
    assert len(enrollments_archive) == len(context['enrollments_archive'])
    assert set(enrollments_archive) == set(context['enrollments_archive'])
    assert len(cos_available) == len(context['course_list_available'])
    assert set(cos_available) == set(context['course_list_available'])
