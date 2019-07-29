import copy
import unittest

import factory
import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.encoding import smart_text, smart_bytes

from core.admin import get_admin_url
from core.tests.utils import CSCTestCase
from core.urls import reverse
from courses.tests.factories import CourseFactory
from learning.settings import StudentStatuses, GradeTypes
from learning.tests.factories import GraduateProfileFactory
from learning.tests.mixins import MyUtilitiesMixin
from users.constants import Roles
from users.forms import UserCreationForm
from users.models import User, UserGroup
from users.tests.factories import UserFactory, SHADCourseRecordFactory, \
    StudentFactory, add_user_groups, StudentFactory, CuratorFactory


class UserTests(MyUtilitiesMixin, CSCTestCase):
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
                         u"А. В. Иванова")
        user = User(first_name=u"Анна", last_name=u"Иванова")
        self.assertEqual(user.get_abbreviated_name(),
                         u"А. Иванова")

    def test_short_name(self):
        user = User(first_name="Анна", last_name="Иванова",
                    patronymic="Васильевна")
        non_breaking_space = chr(160)
        assert user.get_short_name() == "Анна Иванова"
        user = User(first_name=u"Анна", last_name=u"Иванова")
        assert user.get_short_name() == "Анна Иванова"

    def test_to_string(self):
        user = User(first_name=u"Анна", last_name=u"Иванова",
                    patronymic=u"Васильевна")
        self.assertEqual(smart_text(user), user.get_full_name(True))

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
        add_user_groups(good_user, [Roles.GRADUATE])
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
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        url = reverse('teaching:assignment_list')
        self.assertLoginRedirect(url)
        response = self.client.post(reverse('login'), user_data)
        assert response.status_code == 200
        self.assertLoginRedirect(url)
        add_user_groups(user, [Roles.STUDENT])
        user.city_id = 'spb'
        user.save()
        response = self.client.post(reverse('login'), user_data)
        assert response.status_code == 302
        resp = self.client.get(reverse('teaching:assignment_list'))
        self.assertLoginRedirect(url)
        add_user_groups(user, [Roles.STUDENT, Roles.TEACHER])
        user.save()
        resp = self.client.get(reverse('teaching:assignment_list'))
        # Teacher has no course offering and redirects to courses list
        self.assertEqual(resp.status_code, 302)
        # Now he has one
        CourseFactory.create(teachers=[user])
        resp = self.client.get(reverse('teaching:assignment_list'))
        self.assertEqual(resp.status_code, 200)

    def test_logout_works(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        login = self.client.login(None, **user_data)
        self.assertTrue(login)
        self.assertIn('_auth_user_id', self.client.session)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, settings.LOGOUT_REDIRECT_URL,
                             status_code=302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_redirect_works(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        User.objects.create_user(**user_data)
        login = self.client.login(None, **user_data)
        resp = self.client.get(reverse('logout'),
                               {'next': reverse('video_list')})
        self.assertRedirects(resp, reverse('video_list'), status_code=302)

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
        resp = self.client.get(user.teacher_profile_url())
        self.assertEqual(resp.status_code, 404)
        add_user_groups(user, [Roles.TEACHER])
        user.save()
        resp = self.client.get(user.teacher_profile_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['teacher'], user)

    def test_user_detail_view(self):
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        response = self.client.get(user.get_absolute_url())
        assert response.status_code == 404
        user.add_group(Roles.STUDENT)
        response = self.client.get(user.get_absolute_url())
        assert response.status_code == 200
        assert response.context['profile_user'] == user
        assert not response.context['is_editing_allowed']

    def test_graduate_can_edit_testimonial(self):
        """
        Only graduates can (and should) have "CSC review" field in their
        profiles
        """
        test_review = "CSC are the bollocks"
        user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
        user = User.objects.create_user(**user_data)
        self.client.login(None, **user_data)
        response = self.client.post(user.get_update_profile_url(),
                                    {'testimonial': test_review})
        self.assertRedirects(response, reverse('user_detail', args=[user.pk]),
                             status_code=302)
        response = self.client.get(reverse('user_detail', args=[user.pk]))
        assert smart_bytes(test_review) not in response.content
        add_user_groups(user, [Roles.GRADUATE])
        user.graduation_year = 2014
        user.save()
        GraduateProfileFactory(student=user)
        response = self.client.post(user.get_update_profile_url(),
                                    {'testimonial': test_review})
        self.assertRedirects(response, reverse('user_detail', args=[user.pk]),
                             status_code=302)
        response = self.client.get(reverse('user_detail', args=[user.pk]))
        assert smart_bytes(test_review) in response.content

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

    @unittest.skip("not implemented")
    def test_completed_courses(self):
        """On profile page unauthenticated users cant' see uncompleted or
        failed courses
        """

    def test_email_on_detail(self):
        """Email field should be displayed only to curators (superuser)"""
        student_mail = "student@student.mail"
        student = StudentFactory(email=student_mail)
        self.doLogin(student)
        url = reverse('user_detail', args=[student.pk])
        resp = self.client.get(url)
        self.assertNotContains(resp, student_mail)
        # check with curator credentials
        curator = CuratorFactory()
        self.doLogin(curator)
        resp = self.client.get(url)
        self.assertContains(resp, student_mail)


@pytest.mark.django_db
def test_user_can_update_profile(client, assert_redirect):
    test_note = "The best user in the world"
    user = StudentFactory()
    client.login(user)
    response = client.get(user.get_absolute_url())
    assert response.status_code == 200
    assert response.context['profile_user'] == user
    assert response.context['is_editing_allowed']
    assert smart_bytes(user.get_update_profile_url()) in response.content
    response = client.get(user.get_update_profile_url())
    assert b'bio' in response.content
    form_data = {'bio': test_note}
    response = client.post(user.get_update_profile_url(), form_data)
    assert_redirect(response, user.get_absolute_url())
    response = client.get(user.get_absolute_url())
    assert smart_bytes(test_note) in response.content


@pytest.mark.django_db
def test_shads(client):
    """
    Students should have "shad courses" on profile page
    """
    student = StudentFactory()
    sc = SHADCourseRecordFactory(student=student, grade=GradeTypes.GOOD)
    response = client.get(student.get_absolute_url())
    assert smart_bytes(sc.name) in response.content
    assert smart_bytes(sc.teachers) in response.content
    # Bad grades should be visible for authenticated users only
    sc.grade = GradeTypes.UNSATISFACTORY
    sc.save()
    response = client.get(student.get_absolute_url())
    assert smart_bytes(sc.name) not in response.content
    student2 = StudentFactory()
    client.login(student2)
    response = client.get(student.get_absolute_url())
    assert smart_bytes(sc.name) in response.content


@pytest.mark.django_db
def test_student_should_have_enrollment_year(admin_client):
    """
    If user set "student" group (pk=1 in initial_data fixture), they
    should also provide an enrollment year, otherwise they should get
    ValidationError
    """
    user = UserFactory(photo='/a/b/c')
    assert user.groups.count() == 0
    form_data = {k: v for k, v in model_to_dict(user).items() if v is not None}
    del form_data['photo']
    form_data.update({
        # Django wants all inline formsets
        'userstatuslog_set-INITIAL_FORMS': '0',
        'userstatuslog_set-TOTAL_FORMS': '0',
        'onlinecourserecord_set-INITIAL_FORMS': '0',
        'onlinecourserecord_set-TOTAL_FORMS': '0',
        'shadcourserecord_set-TOTAL_FORMS': '0',
        'shadcourserecord_set-INITIAL_FORMS': '0',
        'groups-TOTAL_FORMS': '1',
        'groups-INITIAL_FORMS': '0',
        'groups-MAX_NUM_FORMS': '',
        'groups-0-user': user.pk,
        'groups-0-role': Roles.STUDENT,
        'groups-0-site': settings.SITE_ID,
    })
    admin_url = get_admin_url(user)
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 200

    # Empty user.city_id and enrollment_year
    def get_user_group_formset(response):
        form = None
        for inline_formset_obj in response.context['inline_admin_formsets']:
            if issubclass(inline_formset_obj.formset.model, UserGroup):
                form = inline_formset_obj.formset
        return form
    user_group_form = get_user_group_formset(response)
    assert user_group_form, "Inline form for UserGroup is missing"
    assert not user_group_form.is_valid()
    form_data.update({'enrollment_year': 2010})
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 200
    user_group_form = get_user_group_formset(response)
    assert user_group_form, "Inline form for UserGroup is missing"
    assert not user_group_form.is_valid()
    user.refresh_from_db()
    assert user.groups.count() == 0
    form_data.update({'city': 'spb'})
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.groups.count() == 1
