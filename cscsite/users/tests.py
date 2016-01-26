# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re
import unittest
import copy

from itertools import chain

import pytest
from django.test import TestCase
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.utils.encoding import smart_text
from django.utils import translation
from django.utils.translation import ugettext as _

from bs4 import BeautifulSoup
import factory
from icalendar import Calendar, Event
from learning.settings import PARTICIPANT_GROUPS
from learning.factories import StudentProjectFactory, SemesterFactory, \
    CourseOfferingFactory, CourseClassFactory, EnrollmentFactory, \
    AssignmentFactory, NonCourseEventFactory, CourseFactory
from learning.tests.mixins import MyUtilitiesMixin

from .admin import CSCUserCreationForm, CSCUserChangeForm
from .models import CSCUser, CSCUserReference
from .factories import UserFactory, SHADCourseRecordFactory, \
    CSCUserReferenceFactory


class CustomSemesterFactory(SemesterFactory):
    type = factory.Iterator(['spring', 'autumn'])


class UserTests(MyUtilitiesMixin, TestCase):
    def test_groups_pks_synced_with_migrations(self):
        """
        We need to be sure, that migrations creates groups with desired pk's.
        Not so actual for prod db, but we still should check it.
        """
        with translation.override('en'):
            self.assertEqual(CSCUser.group_pks[CSCUser.group_pks.STUDENT_CENTER],
                             Group.objects.get(pk=1).name)
            self.assertEqual(CSCUser.group_pks[CSCUser.group_pks.TEACHER_CENTER],
                             Group.objects.get(pk=2).name)
            self.assertEqual(CSCUser.group_pks[CSCUser.group_pks.GRADUATE_CENTER],
                             Group.objects.get(pk=3).name)
            self.assertEqual(CSCUser.group_pks[CSCUser.group_pks.VOLUNTEER],
                             Group.objects.get(pk=4).name)
            self.assertEqual(CSCUser.group_pks[CSCUser.group_pks.STUDENT_CLUB],
                             Group.objects.get(pk=5).name)
            self.assertEqual(CSCUser.group_pks[CSCUser.group_pks.TEACHER_CLUB],
                             Group.objects.get(pk=6).name)

    def test_student_should_have_enrollment_year(self):
        """
        If user set "student" group (pk=1 in initial_data fixture), they
        should also provide an enrollment year, otherwise they should get
        ValidationError
        """
        user = UserFactory()
        user_data = model_to_dict(user)
        user_data.update({
            'groups': [user.group_pks.STUDENT_CENTER],
        })
        form = CSCUserChangeForm(user_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('enrollment_year', form.errors.keys())
        user_data.update({'enrollment_year': 2010})
        form = CSCUserChangeForm(user_data, instance=user)
        self.assertTrue(form.is_valid())

    def test_graduate_should_have_graduation_year(self):
        """
        If user set "graduate" group (pk=3 in initial_data fixture), they
        should also provide graduation year, otherwise they should get
        ValidationError
        """
        user = UserFactory()
        user_data = model_to_dict(user)
        user_data.update({
            'groups': [user.group_pks.GRADUATE_CENTER],
        })
        form = CSCUserChangeForm(user_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('graduation_year', form.errors.keys())
        user_data.update({'graduation_year': 2015})
        form = CSCUserChangeForm(user_data, instance=user)
        self.assertTrue(form.is_valid())

    def test_full_name_contains_patronymic(self):
        """
        If "patronymic" is set, get_full_name's result should contain it
        """
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова",
                       patronymic=u"Васильевна")
        self.assertEqual(user.get_full_name(), u"Анна Васильевна Иванова")
        self.assertEqual(user.get_full_name(True), u"Иванова Анна Васильевна")
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_full_name(), u"Анна Иванова")

    def test_abbreviated_name(self):
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова",
                       patronymic=u"Васильевна")
        self.assertEqual(user.get_abbreviated_name(),
                         u"А.В.Иванова")
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_abbreviated_name(),
                         u"А.Иванова")

    def test_short_name(self):
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова",
                       patronymic=u"Васильевна")
        self.assertEqual(user.get_short_name(),
                         u"Иванова Анна")
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_short_name(),
                         u"Иванова Анна")

    def test_to_string(self):
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова",
                       patronymic=u"Васильевна")
        self.assertEqual(smart_text(user), user.get_full_name(True))

    def test_group_props(self):
        """
        Tests properties based on groups (is_student, is_graduate, is_teacher)
        """
        user = CSCUser(username="foo")
        user.save()
        self.assertFalse(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = CSCUser(username="bar")
        user.save()
        user.groups = [user.group_pks.STUDENT_CENTER]
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = CSCUser(username="baz")
        user.save()
        user.groups = [user.group_pks.STUDENT_CENTER, user.group_pks.TEACHER_CENTER]
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = CSCUser(username="baq")
        user.save()
        user.groups = [user.group_pks.STUDENT_CENTER, user.group_pks.TEACHER_CENTER,
                       user.group_pks.GRADUATE_CENTER]
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertTrue(user.is_graduate)

    @unittest.skip('not implemented')
    def test_expelled(self):
        """User cant access student section if his status is expelled"""
        pass

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        soup = BeautifulSoup(response.content, "html.parser")
        maybe_form = soup.find_all("form")
        self.assertEqual(len(maybe_form), 1)
        form = maybe_form[0]
        self.assertEqual(len(form.select('input[name="username"]')), 1)
        self.assertEqual(len(form.select('input[name="password"]')), 1)
        self.assertEqual(len(form.select('input[type="submit"]')), 1)

    def test_login_works(self):
        good_user = UserFactory.attributes()
        CSCUser.objects.create_user(**good_user)
        self.assertNotIn('_auth_user_id', self.client.session)
        bad_user = copy.copy(good_user)
        bad_user['password'] = "BAD"
        resp = self.client.post(reverse('login'), bad_user)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(resp.status_code, 200)
        assert len(resp.context['form'].errors) > 0
        resp = self.client.post(reverse('login'), good_user)
        self.assertRedirects(resp, settings.LOGIN_REDIRECT_URL)
        self.assertIn('_auth_user_id', self.client.session)

    def test_auth_restriction_works(self):
        def assertLoginRedirect(url):
            self.assertRedirects(self.client.get(url),
                                 "{}?next={}".format(settings.LOGIN_URL, url))
        user_data = UserFactory.attributes()
        user = CSCUser.objects.create_user(**user_data)
        url = reverse('assignment_list_teacher')
        assertLoginRedirect(url)
        self.client.post(reverse('login'), user_data)
        assertLoginRedirect(url)
        user.groups = [user.group_pks.STUDENT_CENTER]
        user.save()
        resp = self.client.get(reverse('assignment_list_teacher'))
        assertLoginRedirect(url)
        user.groups = [user.group_pks.STUDENT_CENTER, user.group_pks.TEACHER_CENTER]
        user.save()
        resp = self.client.get(reverse('assignment_list_teacher'))
        self.assertEqual(resp.status_code, 200)

    def test_logout_works(self):
        user_data = UserFactory.attributes()
        CSCUser.objects.create_user(**user_data)
        login = self.client.login(**user_data)
        self.assertTrue(login)
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, settings.LOGOUT_REDIRECT_URL,
                             status_code=301)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_redirect_works(self):
        user_data = UserFactory.attributes()
        CSCUser.objects.create_user(**user_data)
        login = self.client.login(**user_data)
        resp = self.client.get(reverse('logout'),
                               {'next': reverse('course_video_list')})
        self.assertRedirects(resp, reverse('course_video_list'),
                             status_code=301)

    def test_yandex_id_from_email(self):
        """
        yandex_id can be exctracted from email if email is on @yandex.ru
        """
        user = CSCUser.objects.create_user("testuser1", "foo@bar.net",
                                           "test123foobar@!")
        self.assertFalse(user.yandex_id)
        user = CSCUser.objects.create_user("testuser2", "foo@yandex.ru",
                                           "test123foobar@!")
        self.assertEqual(user.yandex_id, "foo")

    def test_short_note(self):
        """
        get_short_note should split note on first paragraph
        """
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        user.note = "Some small text"
        self.assertEqual(user.get_short_note(), "Some small text")
        user.note = """Some large text.

        It has several paragraphs, by the way."""
        self.assertEqual(user.get_short_note(), "Some large text.")

    def test_teacher_detail_view(self):
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        resp = self.client.get(reverse('teacher_detail', args=[user.pk]))
        self.assertEqual(resp.status_code, 404)
        user.groups = [user.group_pks.TEACHER_CENTER]
        user.save()
        resp = self.client.get(reverse('teacher_detail', args=[user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['teacher'], user)

    def test_user_detail_view(self):
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['user_object'], user)
        self.assertFalse(resp.context['is_extended_profile_available'])
        self.assertFalse(resp.context['is_editing_allowed'])

    def test_user_can_update_profile(self):
        test_note = "The best user in the world"
        user_data = UserFactory.attributes()
        user = CSCUser.objects.create_user(**user_data)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertFalse(resp.context['is_extended_profile_available'])
        self.client.login(**user_data)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertEqual(resp.context['user_object'], user)
        self.assertTrue(resp.context['is_extended_profile_available'])
        self.assertTrue(resp.context['is_editing_allowed'])
        self.assertContains(resp, reverse('user_update', args=[user.pk]))
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertContains(resp, 'note')
        resp = self.client.post(reverse('user_update', args=[user.pk]),
                                {'note': test_note})
        self.assertRedirects(resp, reverse('user_detail', args=[user.pk]),
                             status_code=302)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertContains(resp, test_note)

    def test_graduate_can_edit_csc_review(self):
        """
        Only graduates can (and should) have "CSC review" field in their
        profiles
        """
        test_review = "CSC are the bollocks"
        user_data = UserFactory.attributes()
        user = CSCUser.objects.create_user(**user_data)
        self.client.login(**user_data)
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertNotContains(resp, 'csc_review')
        user.groups = [user.group_pks.GRADUATE_CENTER]
        user.graduation_year = 2014
        user.save()
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertIn(b'csc_review', resp.content)
        resp = self.client.post(reverse('user_update', args=[user.pk]),
                                {'csc_review': test_review})
        self.assertRedirects(resp, reverse('user_detail', args=[user.pk]),
                             status_code=302)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertContains(resp, test_review)

    def test_duplicate_check(self):
        """
        It should be impossible to create users with equal names
        """
        user = UserFactory()
        form_data = {'username': user.username,
                     'password1': "test123foobar@!",
                     'password2': "test123foobar@!"}
        form = CSCUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        form_data.update({'username': 'testuser2'})
        form = CSCUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_projects(self):
        """
        Students should have "student projects" in their info
        """
        user = UserFactory(groups=[CSCUser.group_pks.STUDENT_CENTER],
                           enrollment_year='2013')
        semester1 = SemesterFactory.create(year=2014, type='spring')
        semester2 = SemesterFactory.create(year=2014, type='autumn')
        sp1 = StudentProjectFactory.create(students=[user], semester=semester1)
        sp2 = StudentProjectFactory.create(students=[user],
                                           semester=semester2,
                                           description="")
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertContains(resp, sp1.name)
        self.assertContains(resp, sp1.description)
        self.assertContains(resp, sp2.name)

    def test_shads(self):
        """
        Students should have "shad courses" in profile page
        """
        user = UserFactory(groups=[CSCUser.group_pks.STUDENT_CENTER],
                           enrollment_year='2013')
        sc = SHADCourseRecordFactory(student=user)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertContains(resp, sc.name)
        self.assertContains(resp, sc.teachers)

    @unittest.skip("not implemented")
    def test_completed_courses(self):
        """On profile page unauthenticated users cant' see uncompleted or
        failed courses
        """

    def test_email_on_detail(self):
        """Email field should be displayed only to curators (superuser)"""
        student_mail = "student@student.mail"
        student = UserFactory.create(
            groups=['Student [CENTER]'],
            email = student_mail)
        self.doLogin(student)
        url = reverse('user_detail', args=[student.pk])
        resp = self.client.get(url)
        self.assertNotContains(resp, student_mail)
        # check with curator credentials
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        self.doLogin(curator)
        resp = self.client.get(url)
        self.assertContains(resp, student_mail)

@pytest.mark.django_db
def test_prevent_show_club_students_profiles_on_cscenter_site(client,
                                                              user_factory,
                                                              student_club_factory,
                                                              student_factory):
    student_club = student_club_factory.create()
    url = reverse('user_detail', args=[student_club.pk])
    response = client.get(url)
    assert response.status_code == 404
    student = student_factory()
    url = reverse('user_detail', args=[student.pk])
    response = client.get(url)
    assert response.status_code == 200



class ICalTests(MyUtilitiesMixin, TestCase):
    def test_classes(self):
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        user.groups = [user.group_pks.STUDENT_CENTER, user.group_pks.TEACHER_CENTER]
        user.save()
        fname = 'csc_classes.ics'
        # Empty calendar
        resp = self.client.get(reverse('user_ical_classes', args=[user.pk]))
        self.assertEquals("text/calendar; charset=UTF-8", resp['content-type'])
        self.assertIn(fname, resp['content-disposition'])
        cal = Calendar.from_ical(resp.content)
        self.assertEquals("Занятия CSC", cal['X-WR-CALNAME'])
        # Create some content
        ccs_teaching = (CourseClassFactory
                        .create_batch(2, course_offering__teachers=[user]))
        co_learning = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=user, course_offering=co_learning)
        ccs_learning = (CourseClassFactory
                        .create_batch(3, course_offering=co_learning))
        ccs_other = CourseClassFactory.create_batch(5)
        resp = self.client.get(reverse('user_ical_classes', args=[user.pk]),
                               HTTP_HOST = 'test.com')
        cal = Calendar.from_ical(resp.content)
        self.assertSameObjects([cc.name
                                for cc in chain(ccs_teaching, ccs_learning)],
                               [evt['SUMMARY']
                                for evt in cal.subcomponents
                                if isinstance(evt, Event)])

    def test_assignments(self):
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        user.groups = [user.group_pks.STUDENT_CENTER, user.group_pks.TEACHER_CENTER]
        user.save()
        fname = 'csc_assignments.ics'
        # Empty calendar
        resp = self.client.get(reverse('user_ical_assignments', args=[user.pk]))
        self.assertEquals("text/calendar; charset=UTF-8", resp['content-type'])
        self.assertIn(fname, resp['content-disposition'])
        cal = Calendar.from_ical(resp.content)
        self.assertEquals("Задания CSC", cal['X-WR-CALNAME'])
        # Create some content
        as_teaching = (AssignmentFactory
                       .create_batch(2, course_offering__teachers=[user]))
        co_learning = CourseOfferingFactory.create()
        EnrollmentFactory.create(student=user, course_offering=co_learning)
        as_learning = (AssignmentFactory
                       .create_batch(3, course_offering=co_learning))
        as_other = AssignmentFactory.create_batch(5)
        resp = self.client.get(reverse('user_ical_assignments', args=[user.pk]),
                               HTTP_HOST = 'test.com')
        cal = Calendar.from_ical(resp.content)
        self.assertSameObjects(["{} ({})".format(a.title,
                                                 a.course_offering.course.name)
                                for a in chain(as_teaching, as_learning)],
                               [evt['SUMMARY']
                                for evt in cal.subcomponents
                                if isinstance(evt, Event)])

    def test_assignments(self):
        fname = 'csc_events.ics'
        # Empty calendar
        resp = self.client.get(reverse('ical_events'))
        self.assertEquals("text/calendar; charset=UTF-8", resp['content-type'])
        self.assertIn(fname, resp['content-disposition'])
        cal = Calendar.from_ical(resp.content)
        self.assertEquals("События CSC", cal['X-WR-CALNAME'])
        # Create some content
        nces = NonCourseEventFactory.create_batch(3)
        resp = self.client.get(reverse('ical_events'), HTTP_HOST = 'test.com')
        cal = Calendar.from_ical(resp.content)
        self.assertSameObjects([nce.name for nce in nces],
                               [evt['SUMMARY']
                                for evt in cal.subcomponents
                                if isinstance(evt, Event)])


class UserReferenceTests(MyUtilitiesMixin, TestCase):
    def test_user_detail_view(self):
        """Show reference-add button only to curators (superusers)"""
        # check user page without curator credentials
        student = UserFactory.create(groups=['Student [CENTER]'], enrollment_year=2011)
        self.doLogin(student)
        url = reverse('user_detail', args=[student.pk])
        response = self.client.get(url)
        self.assertEquals(response.context['has_curator_permissions'], False)
        soup = BeautifulSoup(response.content, "html.parser")
        button = soup.find('a', text=_("Create reference"))
        self.assertIsNone(button)
        # check with curator credentials
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        self.doLogin(curator)
        response = self.client.get(url)
        self.assertEquals(response.context['has_curator_permissions'], True)
        soup = BeautifulSoup(response.content, "html.parser")
        button = soup.find(string=re.compile(_("Create reference")))
        self.assertIsNotNone(button)

    def test_user_detail_reference_list_view(self):
        """Check reference list appears on student profile page for curators only"""
        student = UserFactory.create(groups=['Student [CENTER]'])
        EnrollmentFactory.create()
        CSCUserReferenceFactory.create(student=student)
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        url = reverse('user_detail', args=[student.pk])
        self.doLogin(curator)
        response = self.client.get(url)
        self.assertEquals(
            response.context['user_object'].cscuserreference_set.count(), 1)
        soup = BeautifulSoup(response.content, "html.parser")
        list_header = soup.find('h4', text=re.compile(_("Student references")))
        self.assertIsNotNone(list_header)
        self.doLogin(student)
        response = self.client.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        list_header = soup.find('h4', text=_("Student references"))
        self.assertIsNone(list_header)

    def test_create_reference(self):
        """Check FIO substitues in signature input field
           Check redirect to reference detail after form submit
        """
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        self.doLogin(curator)
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        form_url = reverse('user_reference_add', args=[user.id])
        response = self.client.get(form_url)
        soup = BeautifulSoup(response.content, "html.parser")
        sig_input = soup.find(id="id_signature")
        self.assertEquals(sig_input.attrs.get('value'), curator.get_full_name())

        student = UserFactory.create(groups=['Student [CENTER]'])
        reference = CSCUserReferenceFactory.build(student=student)
        expected_reference_id = 1
        form_url = reverse('user_reference_add', args=[student.id])
        form_data = model_to_dict(reference)
        response = self.client.post(form_url, form_data)
        self.assertRedirects(response,
            reverse('user_reference_detail',
                    args=[student.id, expected_reference_id])
        )

    def test_reference_detail(self):
        """Check enrollments duplicates, reference fields"""
        student = UserFactory.create(groups=[CSCUser.group_pks.STUDENT_CENTER])
        # add 2 enrollments from 1 course reading exactly
        course = CourseFactory.create()
        semesters = (CustomSemesterFactory.create_batch(2, year=2014))
        enrollments = []
        for s in semesters:
            e = EnrollmentFactory.create(
                course_offering=CourseOfferingFactory.create(
                    course=course,
                    semester=s),
                student=student,
                grade='good'
            )
            enrollments.append(e)
        reference = CSCUserReferenceFactory.create(
            student=student,
            note="TEST",
            signature="SIGNATURE")
        url = reverse('user_reference_detail',
                             args=[student.id, reference.id])
        self.doLogin(student)
        self.assertLoginRedirect(url)
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        self.doLogin(curator)
        response  = self.client.get(url)
        self.assertEqual(response.context['object'].note, "TEST")
        soup = BeautifulSoup(response.content, "html.parser")
        sig_text = soup.find(text=re.compile('SIGNATURE'))
        self.assertIsNotNone(sig_text)
        es = soup.find(id='reference-page-body').findAll('li')
        expected_enrollments_count = 1
        self.assertEquals(len(es), expected_enrollments_count)

    def test_club_student_login_on_cscenter_site(self):
        student = UserFactory.create(is_superuser=False, is_staff=False,
            groups=[CSCUser.group_pks.STUDENT_CLUB])
        self.doLogin(student)
        login_data = {
            'username': student.username,
            'password': student.raw_password
        }
        response = self.client.post(reverse('login'), login_data)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        # can't login message in __all__
        self.assertIn("__all__", form.errors)
        student.groups = [CSCUser.group_pks.STUDENT_CENTER]
        student.save()
        response = self.client.post(reverse('login'), login_data)
        self.assertEqual(response.status_code, 302)
