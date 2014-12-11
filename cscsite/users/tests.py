# -*- coding: utf-8 -*-

from django.test import TestCase
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from bs4 import BeautifulSoup
import factory

from learning.tests.factories import StudentProjectFactory, SemesterFactory

from .models import CSCUser
from .admin import CSCUserCreationForm


class UserFactory(factory.Factory):
    class Meta:
        model = CSCUser

    username = "testuser"
    password = "test123foobar@!"
    email = "foo@bar.net"


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
        user.enrollment_year = 2010
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

    def test_login_works(self):
        CSCUser.objects.create_user(**UserFactory.attributes())
        self.assertNotIn('_auth_user_id', self.client.session)
        bad_user = UserFactory.attributes()
        bad_user['password'] = "BAD"
        resp = self.client.post(reverse('login'),
                                bad_user)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "alert")
        resp = self.client.post(reverse('login'),
                                UserFactory.attributes())
        self.assertRedirects(resp, settings.LOGIN_REDIRECT_URL)
        self.assertIn('_auth_user_id', self.client.session)

    def test_auth_restriction_works(self):
        def assertLoginRedirect(url):
            self.assertRedirects(self.client.get(url),
                                 "{}?next={}".format(settings.LOGIN_URL, url))

        user = CSCUser.objects.create_user(**UserFactory.attributes())
        url = reverse('assignment_list_teacher')
        assertLoginRedirect(url)
        self.client.post(reverse('login'), UserFactory.attributes())
        assertLoginRedirect(url)
        user.groups = [user.IS_STUDENT_PK]
        user.save()
        resp = self.client.get(reverse('assignment_list_teacher'))
        assertLoginRedirect(url)
        user.groups = [user.IS_STUDENT_PK, user.IS_TEACHER_PK]
        user.save()
        resp = self.client.get(reverse('assignment_list_teacher'))
        self.assertEqual(resp.status_code, 200)

    def test_logout_works(self):
        CSCUser.objects.create_user(**UserFactory.attributes())
        login = self.client.login(**UserFactory.attributes())
        self.assertTrue(login)
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, settings.LOGOUT_REDIRECT_URL,
                             status_code=301)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_redirect_works(self):
        CSCUser.objects.create_user(**UserFactory.attributes())
        login = self.client.login(**UserFactory.attributes())
        resp = self.client.get(reverse('logout'),
                               {'next': reverse('enrollment')})
        self.assertRedirects(resp, reverse('enrollment'),
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
        user.groups = [user.IS_TEACHER_PK]
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
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        self.client.login(**UserFactory.attributes())
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
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        self.client.login(**UserFactory.attributes())
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertNotContains(resp, 'csc_review')
        user.groups = [user.IS_GRADUATE_PK]
        user.graduation_year = 2014
        user.save()
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertIn('csc_review', resp.content)
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
        CSCUser.objects.create_user(**UserFactory.attributes())
        form_data = {'username': "testuser",
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
        user = CSCUser.objects.create_user(**UserFactory.attributes())
        user.groups = [user.IS_STUDENT_PK]
        user.save()
        semester1 = SemesterFactory.create(year=2014, type='spring')
        semester2 = SemesterFactory.create(year=2014, type='autumn')
        sp1 = StudentProjectFactory.create(student=user, semesters=[])
        sp2 = StudentProjectFactory.create(student=user,
                                           semesters=[semester1, semester2],
                                           description="")
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertContains(resp, sp1.name)
        self.assertContains(resp, sp1.description)
        self.assertContains(resp, sp2.name)
