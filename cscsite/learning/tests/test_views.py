# -*- coding: utf-8 -*-
import logging
import os
import unittest

import pytest
import pytz
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
from learning.tests.utils import check_url_security
from users.factories import TeacherCenterFactory, StudentFactory, \
    StudentCenterFactory, StudentClubFactory, GraduateFactory
from .mixins import *
from ..factories import *


# TODO: Список отображаемых курсов для центра/клуба
# TODO: Написать тест, который проверяет, что по-умолчанию в форму
# редактирования описания ПРОЧТЕНИЯ подставляется описание из курса. И описание прочтения, если оно уже есть.
# TODO: test redirects on course offering page if tab exists but user has no access
# TODO: test assignment deadline




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
        CourseClassFactory.create_batch(3, course__teachers=[teacher],
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
        CourseClassFactory.create_batch(2, course__teachers=[teacher],
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
        co = CourseFactory.create()
        e = EnrollmentFactory.create(course=co, student=student)
        self.assertEqual(0, len(self.client.get(reverse('timetable_student'))
                                .context['object_list']))
        today_date = (datetime.datetime.now().replace(tzinfo=timezone.utc))
        CourseClassFactory.create_batch(3, course=co, date=today_date)
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
        CourseClassFactory.create_batch(2, course=co, date=next_week_date)
        self.assertEqual(2, len(self.client.get(next_week_url)
                                .context['object_list']))


@pytest.mark.django_db
def test_video_list(client):
    CourseFactory.create_batch(2, is_published_in_video=False)
    with_video = CourseFactory.create_batch(5,
                                            is_published_in_video=True)
    response = client.get(reverse('course_video_list'))
    co_to_show = response.context['object_list']
    assert len(co_to_show) == 5
    assert set(with_video) == set(co_to_show)


class CourseListTeacherTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'course_list_teacher'
    groups_allowed = [PARTICIPANT_GROUPS.TEACHER_CENTER]


class MetaCourseDetailTests(MyUtilitiesMixin, TestCase):
    def test_meta_course_detail(self):
        mc = MetaCourseFactory.create()
        s1 = SemesterFactory(year=2016)
        s2 = SemesterFactory(year=2017)
        co1 = CourseFactory(semester=s1, meta_course=mc,
                            city=settings.DEFAULT_CITY_CODE)
        co2 = CourseFactory(semester=s2, meta_course=mc,
                            city=settings.DEFAULT_CITY_CODE)
        response = self.client.get(mc.get_absolute_url())
        self.assertContains(response, mc.name)
        self.assertContains(response, mc.description)
        # Course offerings not repeated, used set to compare
        assert {c.pk for c in response.context['offerings']} == {co1.pk, co2.pk}
        co2.city_id = "kzn"
        co2.save()
        response = self.client.get(mc.get_absolute_url())
        if settings.SITE_ID == settings.CENTER_SITE_ID:
            assert {c.pk for c in response.context['offerings']} == {co1.pk}


class MetaCourseUpdateTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        mc = MetaCourseFactory.create()
        url = reverse('meta_course_edit', args=[mc.slug])
        all_test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
            [PARTICIPANT_GROUPS.GRADUATE_CENTER]
        ]
        for groups in all_test_groups:
            self.doLogin(UserFactory.create(groups=groups, city_id='spb'))
            self.assertPOSTLoginRedirect(url, {})
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        self.assertEqual(
            200, self.client.post(url, {'name': "foobar"}).status_code)

    def test_update(self):
        mc = MetaCourseFactory.create()
        url = reverse('meta_course_edit', args=[mc.slug])
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        fields = model_to_dict(mc)
        # Note: Create middleware for lang request support in cscenter app
        # or define locale value explicitly
        fields.update({'name_ru': "foobar"})
        self.assertEqual(302, self.client.post(url, fields).status_code)
        self.assertEqual("foobar", MetaCourse.objects.get(pk=mc.pk).name_ru)


class CourseDetailTests(MyUtilitiesMixin, TestCase):
    def test_basic_get(self):
        co = CourseFactory.create()
        assert 200 == self.client.get(co.get_absolute_url()).status_code
        url = city_aware_reverse('course_detail', kwargs={
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
        co = CourseFactory.create()
        co_other = CourseFactory.create()
        url = co.get_absolute_url()
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        self.doLogin(student)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        EnrollmentFactory.create(student=student, course=co_other)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        EnrollmentFactory.create(student=student, course=co)
        ctx = self.client.get(url).context
        self.assertEqual(True, ctx['request_user_enrollment'] is not None)
        self.assertEqual(False, ctx['is_actual_teacher'])
        self.client.logout()
        self.doLogin(teacher)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        CourseTeacherFactory(course=co_other, teacher=teacher)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        CourseTeacherFactory(course=co, teacher=teacher)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(True, ctx['is_actual_teacher'])

    def test_assignment_list(self):
        student = StudentCenterFactory()
        teacher = TeacherCenterFactory()
        next_day = now() + datetime.timedelta(days=1)
        co = CourseFactory.create(teachers=[teacher],
                                  completed_at=next_day)
        url = co.get_absolute_url()
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        self.assertNotContains(self.client.get(url), a.title)
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.title)
        a_s = StudentAssignment.objects.get(assignment=a, student=student)
        self.assertContains(self.client.get(url), a_s.get_student_url())
        a_s.delete()
        with LogCapture(level=logging.INFO) as l:
            self.assertEqual(200, self.client.get(url).status_code)
            l.check(('learning.widgets',
                     'INFO',
                     f"no StudentAssignment for "
                     f"student ID {student.pk}, assignment ID {a.pk}"))
        self.client.logout()
        self.doLogin(teacher)
        self.assertContains(self.client.get(url), a.title)
        self.assertContains(self.client.get(url),
                            reverse('assignment_detail_teacher', args=[a.pk]))


class CourseEditDescrTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        teacher_other = TeacherCenterFactory()
        co = CourseFactory.create(teachers=[teacher])
        url = co.get_update_url()
        self.assertLoginRedirect(url)
        self.doLogin(teacher_other)
        self.assertLoginRedirect(url)
        self.doLogout()
        self.doLogin(teacher)
        self.assertStatusCode(200, url, make_reverse=False)


class CourseNewsCreateTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = TeacherCenterFactory()
        self.teacher_other = TeacherCenterFactory()
        self.co = CourseFactory.create(teachers=[self.teacher])
        self.url = self.co.get_create_news_url()
        self.n_dict = factory.build(dict, FACTORY_CLASS=CourseNewsFactory)
        self.n_dict.update({'course': self.co})

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
        con = resp.context['course'].coursenews_set.all()[0]
        self.assertEqual(con.author, self.teacher)


class CourseNewsUpdateTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = TeacherCenterFactory()
        self.teacher_other = TeacherCenterFactory()
        self.co = CourseFactory.create(teachers=[self.teacher])
        self.con = CourseNewsFactory.create(course=self.co,
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


class CourseNewsDeleteTests(MyUtilitiesMixin, TestCase):
    def setUp(self):
        self.teacher = TeacherCenterFactory()
        self.teacher_other = TeacherCenterFactory()
        self.co = CourseFactory.create(teachers=[self.teacher])
        self.con = CourseNewsFactory.create(course=self.co,
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
        CourseTeacherFactory(course=cc_other.course,
                             teacher=teacher)
        self.assertEqual(False, self.client.get(url)
                         .context['is_actual_teacher'])
        CourseTeacherFactory(course=cc.course,
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
        co = CourseFactory.create(teachers=[teacher])
        form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
        form.update({'venue': VenueFactory.create().pk})
        url = co.get_create_class_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)

    def test_create(self):
        teacher = TeacherCenterFactory()
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        co_other = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                        semester=s)
        form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
        venue = VenueFactory.create(city_id=settings.DEFAULT_CITY_CODE)
        form.update({'venue': venue.pk})
        del form['slides']
        url = co.get_create_class_url()
        self.doLogin(teacher)
        # should save with course = co
        self.assertEqual(302, self.client.post(url, form).status_code)
        self.assertEqual(1, CourseClass.objects.filter(course=co).count())
        self.assertEqual(0, (CourseClass.objects
                             .filter(course=co_other).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course=form['course']).count()))
        self.assertEqual(CourseClass.objects.get(course=co).name, form['name'])
        form.update({'course': co.pk})
        self.assertEqual(302, self.client.post(url, form).status_code)

    def test_create_and_add(self):
        teacher = TeacherCenterFactory()
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        co_other = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                        semester=s)
        form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
        venue = VenueFactory.create(city_id=settings.DEFAULT_CITY_CODE)
        form.update({'venue': venue.pk, '_addanother': True})
        del form['slides']
        self.doLogin(teacher)
        url = co.get_create_class_url()
        # should save with course = co
        response = self.client.post(url, form)
        expected_url = co.get_create_class_url()
        self.assertEqual(302, response.status_code)
        self.assertRedirects(response, expected_url)
        self.assertEqual(1, CourseClass.objects.filter(course=co).count())
        self.assertEqual(0, (CourseClass.objects
                             .filter(course=co_other).count()))
        self.assertEqual(0, (CourseClass.objects
                             .filter(course=form['course']).count()))
        self.assertEqual(CourseClass.objects.get(course=co).name, form['name'])
        form.update({'course': co.pk})
        self.assertEqual(302, self.client.post(url, form).status_code)
        del form['_addanother']
        response = self.client.post(url, form)
        self.assertEqual(3, CourseClass.objects.filter(course=co).count())
        last_added_class = CourseClass.objects.order_by("-id").first()
        self.assertRedirects(response, last_added_class.get_absolute_url())

    def test_update(self):
        teacher = TeacherCenterFactory()
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course=co)
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
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course=co)
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
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course=co)
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
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course=co)
        base_url = cc.get_update_url()
        self.doLogin(teacher)
        form = model_to_dict(cc)
        del form['slides']
        form['name'] += " foobar"
        self.assertRedirects(self.client.post(base_url, form),
                             cc.get_absolute_url())
        url = ("{}?back=course"
               .format(base_url))
        self.assertRedirects(self.client.post(url, form),
                             co.get_absolute_url())

    def test_attachment_links(self):
        teacher = TeacherCenterFactory()
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course=co)
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
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                  teachers=[teacher], semester=s)
        cc = CourseClassFactory.create(course=co)
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
        student = StudentCenterFactory(city_id='spb')
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory(city_id='spb', semester=s,
                           teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        assert self.client.get(url).status_code == 302
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups, city_id='spb'))
            if not groups:
                assert self.client.get(url).status_code == 302
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(student)
        assert self.client.get(url).status_code == 200
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
        student = StudentFactory(city_id='spb')
        past_year = datetime.datetime.now().year - 3
        past_semester = SemesterFactory.create(year=past_year)
        co = CourseFactory(city_id='spb', teachers=[teacher],
                           semester=past_semester)
        enrollment = EnrollmentFactory(student=student, course=co,
                                       grade=GRADES.unsatisfactory)
        a = AssignmentFactory(course=co)
        s_a = StudentAssignment.objects.get(student=student, assignment=a)
        assert s_a.grade is None
        self.doLogin(student)
        url = s_a.get_student_url()
        response = self.client.get(url)
        self.assertLoginRedirect(url)
        # assert response.status_code == 403
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
        self.assertLoginRedirect(url)
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
        student = StudentCenterFactory(city_id='spb')
        semester = SemesterFactory.create_current()
        co = CourseFactory.create(city_id='spb', semester=semester)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.text)

    def test_teacher_redirect_to_appropriate_link(self):
        student = StudentCenterFactory(city_id='spb')
        teacher = TeacherCenterFactory()
        semester = SemesterFactory.create_current()
        co = CourseFactory(city_id='spb', teachers=[teacher],
                           semester=semester)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        assert self.client.get(url).status_code == 200
        self.doLogin(teacher)
        expected_url = a_s.get_teacher_url()
        self.assertEquals(302, self.client.get(url).status_code)
        self.assertRedirects(self.client.get(url), expected_url)

    def test_comment(self):
        student = StudentCenterFactory(city_id='spb')
        # Create open reading to make sure student has access to CO
        co = CourseFactory(city_id='spb', is_open=True)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
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
        co = CourseFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_teacher_url()
        assert self.client.get(url).status_code == 302
        self.assertLoginRedirect(url)
        # Test GET
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [PARTICIPANT_GROUPS.TEACHER_CENTER]:
                self.assertLoginRedirect(url)
            else:
                assert self.client.get(url).status_code == 302
            self.doLogout()
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)
        self.doLogout()
        self.doLogin(student)
        assert self.client.get(url).status_code == 302
        self.assertLoginRedirect(url)
        self.doLogout()
        # Test POST
        grade_dict = {'grading_form': True, 'grade': 3}
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER]
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [PARTICIPANT_GROUPS.TEACHER_CENTER]:
                self.assertPOSTLoginRedirect(url, grade_dict)
            else:
                assert self.client.get(url).status_code == 302
            self.doLogout()

    def test_comment(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
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
        co = CourseFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co,
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
        co = CourseFactory.create(teachers=[teacher])
        co_other = CourseFactory.create()
        EnrollmentFactory.create(student=student, course=co)
        EnrollmentFactory.create(student=student, course=co_other)
        a1, a2 = AssignmentFactory.create_batch(2, course=co)
        a_other = AssignmentFactory.create(course=co_other)
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
    co = CourseFactory(semester=semester, teachers=[teacher])
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
    venue = VenueFactory(city=co.city)
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
    check_url_security(client, settings,
                       groups_allowed=[PARTICIPANT_GROUPS.STUDENT_CENTER],
                       url=url)
    student_spb = StudentCenterFactory(city_id='spb')
    client.login(student_spb)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['archive_enrolled']) == 0
    now_year, now_season = get_current_term_pair(student_spb.city_id)
    current_term_spb = SemesterFactory.create(year=now_year, type=now_season)
    cos = CourseFactory.create_batch(4, semester=current_term_spb,
                                     city_id='spb', is_open=False)
    cos_available = cos[:2]
    cos_enrolled = cos[2:]
    prev_year = now_year - 1
    cos_archived = CourseFactory.create_batch(
        3, semester__year=prev_year, is_open=False)
    for co in cos_enrolled:
        EnrollmentFactory.create(student=student_spb, course=co)
    for co in cos_archived:
        EnrollmentFactory.create(student=student_spb, course=co)
    response = client.get(url)
    assert len(cos_enrolled) == len(response.context['ongoing_enrolled'])
    assert set(cos_enrolled) == set(response.context['ongoing_enrolled'])
    assert len(cos_archived) == len(response.context['archive_enrolled'])
    assert set(cos_archived) == set(response.context['archive_enrolled'])
    assert len(cos_available) == len(response.context['ongoing_rest'])
    assert set(cos_available) == set(response.context['ongoing_rest'])
    # Add co from other city
    now_year, now_season = get_current_term_pair('nsk')
    current_term_nsk = SemesterFactory.create(year=now_year, type=now_season)
    co_nsk = CourseFactory.create(semester=current_term_nsk,
                                  city_id='nsk', is_open=False)
    response = client.get(url)
    assert len(cos_enrolled) == len(response.context['ongoing_enrolled'])
    assert len(cos_available) == len(response.context['ongoing_rest'])
    assert len(cos_archived) == len(response.context['archive_enrolled'])
    # Test for student from nsk
    student_nsk = StudentCenterFactory(city_id='nsk')
    client.login(student_nsk)
    CourseFactory.create(semester__year=prev_year, city_id='nsk',
                         is_open=False)
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co_nsk}
    assert len(response.context['archive_enrolled']) == 0
    # Add open reading, it should be available on compscicenter.ru
    co_open = CourseFactory.create(semester=current_term_nsk,
                                   city_id='nsk', is_open=True)
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 2
    assert set(response.context['ongoing_rest']) == {co_nsk, co_open}
    assert len(response.context['archive_enrolled']) == 0


@pytest.mark.django_db
def test_student_courses_list_csclub(client, settings, mocker):
    settings.SITE_ID = settings.CLUB_SITE_ID
    # Fix year and term
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    now_fixed = datetime.datetime(2016, month=3, day=8, tzinfo=pytz.utc)
    mocked_timezone.return_value = now_fixed
    now_year, now_season = get_current_term_pair(settings.DEFAULT_CITY_CODE)
    assert now_season == "spring"
    url = reverse('course_list_student')
    student = StudentClubFactory()
    client.login(student)
    # We didn't set city_id for student, but it's OK for compsciclub.ru, we
    # rely on city code from request.city_code
    response = client.get(url)
    assert response.status_code == 200
    # Make sure in tests we fallback to default city which is 'spb'
    assert response.context['request'].city_code == 'spb'
    # Show only open courses
    current_term = SemesterFactory.create_current(
        city_code=settings.DEFAULT_CITY_CODE)
    assert current_term.type == "spring"
    settings.SITE_ID = settings.CENTER_SITE_ID
    co = CourseFactory.create(semester__type=now_season,
                              semester__year=now_year, city_id='nsk',
                              is_open=False)
    settings.SITE_ID = settings.CLUB_SITE_ID
    # compsciclub.ru can't see center courses with default manager
    assert Course.objects.count() == 0
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['archive_enrolled']) == 0
    settings.SITE_ID = settings.CENTER_SITE_ID
    co.is_open = True
    co.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    assert Course.objects.count() == 1
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['archive_enrolled']) == 0
    co.city_id = 'spb'
    co.save()
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co}
    assert len(response.context['archive_enrolled']) == 0
    # Summer courses are hidden for compsciclub.ru
    summer_semester = SemesterFactory.create(year=now_year - 1, type='summer')
    co.semester = summer_semester
    co.save()
    settings.SITE_ID = settings.CENTER_SITE_ID
    co_active = CourseFactory.create(semester__type=now_season,
                                     semester__year=now_year,
                                     city_id='spb',
                                     is_open=True)
    settings.SITE_ID = settings.CLUB_SITE_ID
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co_active}
    assert len(response.context['archive_enrolled']) == 0
    # But student can see them in list if they already enrolled
    EnrollmentFactory.create(student=student, course=co)
    response = client.get(url)
    assert len(response.context['ongoing_rest']) == 1
    assert len(response.context['archive_enrolled']) == 1
    assert set(response.context['archive_enrolled']) == {co}


@pytest.mark.django_db
def test_api_testimonials_smoke(client):
    GraduateFactory(csc_review='test', photo='stub.JPG')
    response = client.get(reverse("api:testimonials"))
    assert response.status_code == 200
