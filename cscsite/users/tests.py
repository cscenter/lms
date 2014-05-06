# -*- coding: utf-8 -*-

from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from bs4 import BeautifulSoup

from .models import CSCUser


class UserTests(TestCase):
    def test_student_should_have_enrollment_year(self):
        """
        If user set "student" group (pk=1 in initial_data fixture), they
        should also provide an enrollment year, otherwise they should get
        ValidationError
        """
        user = CSCUser()
        user.save()
        user.groups = [user.IS_STUDENT_PK]
        self.assertRaises(ValidationError, user.clean)
        user.enrolment_year = 2010
        self.assertIsNone(user.clean())

    def test_graduate_should_have_graduation_year(self):
        """
        If user set "graduate" group (pk=3 in initial_data fixture), they
        should also provide graduation year, otherwise they should get
        ValidationError
        """
        user = CSCUser()
        user.save()
        user.groups = [user.IS_GRADUATE_PK]
        self.assertRaises(ValidationError, user.clean)
        user.graduation_year = 2011
        self.assertIsNone(user.clean())

    def test_full_name_contains_patronymic(self):
        """
        If "patronymic" is set, get_full_name's result should contain it
        """
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова",
                       patronymic=u"Васильевна")
        self.assertEqual(user.get_full_name(), u"Анна Васильевна Иванова")
        user = CSCUser(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_full_name(), u"Анна Иванова")

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
        user.groups = [user.IS_STUDENT_PK]
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = CSCUser(username="baz")
        user.save()
        user.groups = [user.IS_STUDENT_PK, user.IS_TEACHER_PK]
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = CSCUser(username="baq")
        user.save()
        user.groups = [user.IS_STUDENT_PK, user.IS_TEACHER_PK,
                       user.IS_GRADUATE_PK]
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertTrue(user.is_graduate)

    def test_login_page(self):
        resp = self.client.get(reverse('login'))
        soup = BeautifulSoup(resp.content)
        maybe_form = soup.find_all("form")
        self.assertEqual(len(maybe_form), 1)
        form = maybe_form[0]
        self.assertEqual(len(form.select('input[name="username"]')), 1)
        self.assertEqual(len(form.select('input[name="password"]')), 1)
        self.assertEqual(len(form.select('input[type="submit"]')), 1)

    # TODO: test group-restricted pages
    def test_login_works(self):
        test_user = "testuser"
        test_password = "test123foobar@!"
        test_email = "foo@bar.net"
        CSCUser.objects.create_user(test_user, test_email, test_password)
        self.assertNotIn('_auth_user_id', self.client.session)
        resp = self.client.post(reverse('login'),
                                {'username': test_user,
                                 'password': test_password + "BAD"})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "alert")
        resp = self.client.post(reverse('login'),
                                {'username': test_user,
                                 'password': test_password})
        self.assertRedirects(resp, settings.LOGIN_REDIRECT_URL)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_works(self):
        test_user = "testuser"
        test_password = "test123foobar@!"
        test_email = "foo@bar.net"
        CSCUser.objects.create_user(test_user, test_email, test_password)
        login = self.client.login(username=test_user,
                                  password=test_password)
        self.assertTrue(login)
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, settings.LOGOUT_REDIRECT_URL,
                             status_code=301)
        self.assertNotIn('_auth_user_id', self.client.session)
