import copy
import unittest

import factory
import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import Group
from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from django.utils import translation
from django.utils.encoding import smart_text, force_text, smart_bytes

from learning.factories import AreaOfStudyFactory
from courses.factories import CourseFactory
from learning.settings import StudentStatuses, GradeTypes
from users.settings import AcademicRoles
from learning.tests.mixins import MyUtilitiesMixin
from users.forms import UserCreationForm, UserChangeForm
from users.factories import UserFactory, SHADCourseRecordFactory, \
    TeacherCenterFactory, StudentClubFactory, \
    StudentFactory, StudentCenterFactory
from users.models import User


class UserTests(MyUtilitiesMixin, TestCase):
    def test_groups_pks_synced_with_migrations(self):
        """
        We need to be sure, that migrations creates groups with desired pk's.
        Not so actual for prod db, but we still should check it.
        """
        with translation.override('en'):
            self.assertEqual(User.roles.values[User.roles.STUDENT_CENTER],
                             Group.objects.get(pk=1).name)
            self.assertEqual(User.roles.values[User.roles.TEACHER_CENTER],
                             Group.objects.get(pk=2).name)
            self.assertEqual(User.roles.values[User.roles.GRADUATE_CENTER],
                             Group.objects.get(pk=3).name)
            self.assertEqual(User.roles.values[User.roles.VOLUNTEER],
                             Group.objects.get(pk=4).name)
            self.assertEqual(User.roles.values[User.roles.STUDENT_CLUB],
                             Group.objects.get(pk=5).name)
            self.assertEqual(User.roles.values[User.roles.TEACHER_CLUB],
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
            'groups': [user.roles.STUDENT_CENTER],
        })
        form = UserChangeForm(user_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('enrollment_year', form.errors.keys())
        user_data.update({'enrollment_year': 2010})
        form = UserChangeForm(user_data, instance=user)
        assert not form.is_valid()
        assert 'city' in form.errors.keys()
        user_data.update({'city': 'spb'})
        form = UserChangeForm(user_data, instance=user)
        assert form.is_valid()

    def test_graduate_should_have_graduation_year(self):
        """
        If user set "graduate" group (pk=3 in initial_data fixture), they
        should also provide graduation year, otherwise they should get
        ValidationError
        """
        user = UserFactory()
        user_data = model_to_dict(user)
        user_data.update({
            'groups': [user.roles.GRADUATE_CENTER],
        })
        form = UserChangeForm(user_data, instance=user)
        assert not form.is_valid()
        self.assertIn('graduation_year', form.errors.keys())
        user_data.update({'graduation_year': 2015})
        form = UserChangeForm(user_data, instance=user)
        assert not form.is_valid()
        assert 'city' in form.errors.keys()
        user_data.update({'city': 'spb'})
        form = UserChangeForm(user_data, instance=user)
        assert form.is_valid()

    def test_full_name_contains_patronymic(self):
        """
        If "patronymic" is set, get_full_name's result should contain it
        """
        user = User(first_name=u"Анна", last_name=u"Иванова",
                    patronymic=u"Васильевна")
        self.assertEqual(user.get_full_name(), u"Анна Васильевна Иванова")
        self.assertEqual(user.get_full_name(True), u"Иванова Анна Васильевна")
        user = User(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_full_name(), u"Анна Иванова")

    def test_abbreviated_name(self):
        user = User(first_name=u"Анна", last_name=u"Иванова",
                    patronymic=u"Васильевна")
        self.assertEqual(user.get_abbreviated_name(),
                         u"А. В. Иванова")
        user = User(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_abbreviated_name(),
                         u"А. Иванова")

    def test_short_name(self):
        user = User(first_name=u"Анна", last_name=u"Иванова",
                    patronymic=u"Васильевна")
        self.assertEqual(user.get_short_name(),
                         u"Анна Иванова")
        user = User(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_short_name(),
                         u"Анна Иванова")

    def test_to_string(self):
        user = User(first_name=u"Анна", last_name=u"Иванова",
                    patronymic=u"Васильевна")
        self.assertEqual(smart_text(user), user.get_full_name(True))

    def test_group_props(self):
        """
        Tests properties based on groups (is_student, is_graduate, is_teacher)
        """
        user = User(username="foo", email="foo@localhost.ru")
        user.save()
        self.assertFalse(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = User(username="bar", email="bar@localhost.ru")
        user.save()
        user.groups.set([user.roles.STUDENT_CENTER])
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = User(username="baz", email="baz@localhost.ru")
        user.save()
        user.groups.set([user.roles.STUDENT_CENTER, user.roles.TEACHER_CENTER])
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_graduate)
        user = User(username="baq", email="baq@localhost.ru")
        user.save()
        user.groups.set([user.roles.STUDENT_CENTER, user.roles.TEACHER_CENTER,
                         user.roles.GRADUATE_CENTER])
        self.assertTrue(user.is_student)
        self.assertTrue(user.is_teacher)
        self.assertTrue(user.is_graduate)

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
        good_user_attrs = factory.build(dict, FACTORY_CLASS=UserFactory)
        good_user = User.objects.create_user(**good_user_attrs)
        # graduated students redirected to LOGIN_REDIRECT_URL
        good_user.groups.add(AcademicRoles.GRADUATE_CENTER)
        self.assertNotIn('_auth_user_id', self.client.session)
        bad_user = copy.copy(good_user_attrs)
        bad_user['password'] = "BAD"
        resp = self.client.post(reverse('login'), bad_user)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(resp.status_code, 200)
        assert len(resp.context['form'].errors) > 0
        resp = self.client.post(reverse('login'), good_user_attrs)
        self.assertRedirects(resp, settings.LOGIN_REDIRECT_URL)
        self.assertIn('_auth_user_id', self.client.session)

    def test_auth_restriction_works(self):
        def assertLoginRedirect(url):
            self.assertRedirects(self.client.get(url),
                                 "{}?next={}".format(settings.LOGIN_URL, url))
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        url = reverse('assignment_list_teacher')
        assertLoginRedirect(url)
        response = self.client.post(reverse('login'), user_data)
        assert response.status_code == 200
        assertLoginRedirect(url)
        user.groups.set([user.roles.STUDENT_CENTER])
        user.city_id = 'spb'
        user.save()
        response = self.client.post(reverse('login'), user_data)
        assert response.status_code == 302
        resp = self.client.get(reverse('assignment_list_teacher'))
        assertLoginRedirect(url)
        user.groups.set([user.roles.STUDENT_CENTER, user.roles.TEACHER_CENTER])
        user.save()
        resp = self.client.get(reverse('assignment_list_teacher'))
        # Teacher has no course offering and redirects to courses list
        self.assertEqual(resp.status_code, 302)
        # Now he has one
        CourseFactory.create(teachers=[user])
        resp = self.client.get(reverse('assignment_list_teacher'))
        self.assertEqual(resp.status_code, 200)

    def test_logout_works(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        User.objects.create_user(**user_data)
        login = self.client.login(**user_data)
        self.assertTrue(login)
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, settings.LOGOUT_REDIRECT_URL,
                             status_code=302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_redirect_works(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        User.objects.create_user(**user_data)
        login = self.client.login(**user_data)
        resp = self.client.get(reverse('logout'),
                               {'next': reverse('course_video_list')})
        self.assertRedirects(resp, reverse('course_video_list'),
                             status_code=302)

    def test_yandex_id_from_email(self):
        """
        yandex_id can be exctracted from email if email is on @yandex.ru
        """
        user = User.objects.create_user("testuser1", "foo@bar.net",
                                           "test123foobar@!")
        self.assertFalse(user.yandex_id)
        user = User.objects.create_user("testuser2", "foo@yandex.ru",
                                           "test123foobar@!")
        self.assertEqual(user.yandex_id, "foo")

    def test_short_bio(self):
        """
        get_short_bio should split bio on first paragraph
        """
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        user.bio = "Some small text"
        self.assertEqual(user.get_short_bio(), "Some small text")
        user.bio = """Some large text.

        It has several paragraphs, by the way."""
        self.assertEqual(user.get_short_bio(), "Some large text.")

    def test_teacher_detail_view(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        resp = self.client.get(reverse('teacher_detail', args=[user.pk]))
        self.assertEqual(resp.status_code, 404)
        user.groups.set([user.roles.TEACHER_CENTER])
        user.save()
        resp = self.client.get(reverse('teacher_detail', args=[user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['teacher'], user)

    def test_user_detail_view(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile_user'], user)
        self.assertFalse(resp.context['is_editing_allowed'])

    def test_user_can_update_profile(self):
        test_note = "The best user in the world"
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.client.login(**user_data)
        resp = self.client.get(reverse('user_detail', args=[user.pk]))
        self.assertEqual(resp.context['profile_user'], user)
        self.assertTrue(resp.context['is_editing_allowed'])
        self.assertContains(resp, reverse('user_update', args=[user.pk]))
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertContains(resp, 'bio')
        resp = self.client.post(reverse('user_update', args=[user.pk]),
                                {'bio': test_note})
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
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        self.client.login(**user_data)
        resp = self.client.get(reverse('user_update', args=[user.pk]))
        self.assertNotContains(resp, 'csc_review')
        user.groups.set([user.roles.GRADUATE_CENTER])
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
                     'email': user.email,
                     'password1': "test123foobar@!",
                     'password2': "test123foobar@!"}
        form = UserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        new_user = UserFactory.build()
        form_data.update({
            'username': new_user.username,
            'email': new_user.email
        })
        form = UserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_shads(self):
        """
        Students should have "shad courses" on profile page
        """
        student = StudentCenterFactory()
        sc = SHADCourseRecordFactory(student=student, grade=GradeTypes.GOOD)
        response = self.client.get(student.get_absolute_url())
        assert smart_bytes(sc.name) in response.content
        assert smart_bytes(sc.teachers) in response.content
        # Bad grades should be visible for authenticated users only
        sc.grade = GradeTypes.UNSATISFACTORY
        sc.save()
        response = self.client.get(student.get_absolute_url())
        assert smart_bytes(sc.name) not in response.content
        student2 = StudentCenterFactory()
        self.doLogin(student2)
        response = self.client.get(student.get_absolute_url())
        assert smart_bytes(sc.name) in response.content

    @unittest.skip("not implemented")
    def test_completed_courses(self):
        """On profile page unauthenticated users cant' see uncompleted or
        failed courses
        """

    def test_email_on_detail(self):
        """Email field should be displayed only to curators (superuser)"""
        student_mail = "student@student.mail"
        student = StudentCenterFactory.create(email=student_mail)
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
def test_club_students_profiles_on_cscenter_site(client):
    """Only teachers and curators can see club students profiles on cscenter site"""
    student_club = StudentClubFactory.create()
    url = reverse('user_detail', args=[student_club.pk])
    response = client.get(url)
    assert response.status_code == 404

    student = StudentFactory()
    url = reverse('user_detail', args=[student.pk])
    response = client.get(url)
    assert response.status_code == 200
    client.login(student)
    url = reverse('user_detail', args=[student_club.pk])
    response = client.get(url)
    assert response.status_code == 404

    teacher_center = TeacherCenterFactory.create()
    client.login(teacher_center)
    url = reverse('user_detail', args=[student_club.pk])
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_expelled(client, settings):
    """Center students and volunteers can't access student section
    if there status equal expelled"""
    student = StudentCenterFactory(status=StudentStatuses.EXPELLED,
                                   city_id=settings.DEFAULT_CITY_CODE)
    client.login(student)
    url = reverse('course_list_student')
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response["Location"]
    # active student
    active_student = StudentCenterFactory(city_id=settings.DEFAULT_CITY_CODE)
    client.login(active_student)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_alumni(client):
    graduated = UserFactory(groups=[AcademicRoles.GRADUATE_CENTER])
    student_center = StudentCenterFactory()
    url_list_all = reverse('alumni')
    response = client.get(url_list_all)
    assert student_center.last_name not in force_text(response.content)
    assert graduated.last_name in force_text(response.content)
    url = reverse('alumni_by_area_of_study', args=["-"])
    response = client.get(url)
    assert response.status_code == 404
    st1 = AreaOfStudyFactory.create()
    st2 = AreaOfStudyFactory.create()
    url = reverse('alumni_by_area_of_study', args=[st1.code])
    response = client.get(url)
    assert "areas_of_study" in response.context
    assert len(response.context["areas_of_study"]) == 2
    graduated.areas_of_study.add(st1.code)
    url = reverse('alumni_by_area_of_study', args=[st1.code])
    response = client.get(url)
    assert graduated.last_name in force_text(response.content)
    response = client.get(url_list_all)
    assert graduated.last_name in force_text(response.content)
    url = reverse('alumni_by_area_of_study', args=[st2.code])
    response = client.get(url)
    assert graduated.last_name not in force_text(response.content)


@pytest.mark.django_db
def test_login_restrictions(client, settings):
    """Again. Club students and teachers have no access to center site"""
    assert settings.SITE_ID == settings.CENTER_SITE_ID

    user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
    student = User.objects.create_user(**user_data)
    # Try to login without groups at all
    response = client.post(reverse('login'), user_data)
    assert response.status_code == 200
    assert len(response.context["form"].errors) > 0
    # Login as center student
    student.groups.add(AcademicRoles.STUDENT_CENTER)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as center and club student simultaneously
    student.groups.add(AcademicRoles.STUDENT_CLUB)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as volunteer
    student.groups.set([AcademicRoles.VOLUNTEER])
    student.save()
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as volunteer and club students simultaneously
    student.groups.add(AcademicRoles.STUDENT_CLUB)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as graduate only
    student.groups.set([AcademicRoles.GRADUATE_CENTER])
    student.save()
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # graduate and club
    student.groups.add(AcademicRoles.STUDENT_CLUB)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Only club gtfo
    student.groups.set([AcademicRoles.STUDENT_CLUB])
    student.save()
    response = client.post(reverse('login'), user_data, follow=True)
    assert not response.wsgi_request.user.is_authenticated
    # Club teacher
    student.groups.add(AcademicRoles.TEACHER_CLUB)
    response = client.post(reverse('login'), user_data, follow=True)
    assert not response.wsgi_request.user.is_authenticated
    # Center teacher
    student.groups.add(AcademicRoles.TEACHER_CENTER)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    # Just to make sure we have no super user permissions
    assert not response.wsgi_request.user.is_curator
