import copy

import factory
import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.encoding import smart_text, smart_bytes

from core.admin import get_admin_url
from core.models import Branch
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.tests.factories import CourseFactory
from learning.settings import GradeTypes, Branches
from learning.tests.factories import GraduateProfileFactory
from users.constants import Roles, GenderTypes
from users.forms import UserCreationForm
from users.models import User, UserGroup
from users.tests.factories import UserFactory, SHADCourseRecordFactory, \
    add_user_groups, StudentFactory, CuratorFactory, \
    OnlineCourseRecordFactory, StudentProfileFactory


@pytest.mark.django_db
def test_full_name_contains_patronymic(client):
    """
    If "patronymic" is set, get_full_name's result should contain it
    """
    user = User(first_name=u"Анна", last_name=u"Иванова",
                patronymic=u"Васильевна")
    assert user.get_full_name() == u"Анна Васильевна Иванова"
    assert user.get_full_name(True) == u"Иванова Анна Васильевна"
    user = User(first_name=u"Анна", last_name=u"Иванова")
    assert user.get_full_name() == u"Анна Иванова"


@pytest.mark.django_db
def test_abbreviated_name(client):
    user = User(first_name=u"Анна", last_name=u"Иванова",
                patronymic=u"Васильевна")
    assert user.get_abbreviated_name() == "А. В. Иванова"
    user = User(first_name=u"Анна", last_name=u"Иванова")
    assert user.get_abbreviated_name() == "А. Иванова"


@pytest.mark.django_db
def test_short_name(client):
    user = User(first_name="Анна", last_name="Иванова",
                patronymic="Васильевна")
    non_breaking_space = chr(160)
    assert user.get_short_name() == "Анна Иванова"
    user = User(first_name=u"Анна", last_name=u"Иванова")
    assert user.get_short_name() == "Анна Иванова"


@pytest.mark.django_db
def test_to_string(client):
    user = User(first_name=u"Анна", last_name=u"Иванова",
                patronymic=u"Васильевна")
    assert smart_text(user) == user.get_full_name(True)


@pytest.mark.django_db
def test_login_page(client):
    response = client.get(reverse('auth:login'))
    soup = BeautifulSoup(response.content, "html.parser")
    maybe_form = soup.find_all("form")
    assert len(maybe_form) == 1
    form = maybe_form[0]
    assert len(form.select('input[name="username"]')) == 1
    assert len(form.select('input[name="password"]')) == 1
    assert len(form.select('input[type="submit"]')) == 1


@pytest.mark.django_db
def test_login_works(client):
    good_user_attrs = factory.build(dict, FACTORY_CLASS=UserFactory)
    good_user_attrs["branch"] = BranchFactory()
    good_user = UserFactory(**good_user_attrs)
    # graduated students redirected to LOGIN_REDIRECT_URL
    add_user_groups(good_user, [Roles.GRADUATE])
    assert '_auth_user_id' not in client.session
    bad_user = copy.copy(good_user_attrs)
    bad_user['password'] = "BAD"
    response = client.post(reverse('auth:login'), bad_user)
    assert '_auth_user_id' not in client.session
    assert response.status_code == 200
    assert len(response.context['form'].errors) > 0
    response = client.post(reverse('auth:login'), good_user_attrs)
    assert response.status_code == 302
    assert response.url == settings.LOGIN_REDIRECT_URL
    assert '_auth_user_id' in client.session


@pytest.mark.django_db
def test_logout_works(client):
    user = UserFactory()
    client.login(user)
    assert '_auth_user_id' in client.session
    response = client.get(reverse('auth:logout'))
    assert response.status_code == 302
    assert response.url == settings.LOGOUT_REDIRECT_URL
    assert '_auth_user_id' not in client.session


@pytest.mark.django_db
def test_logout_redirect_works(client):
    user = UserFactory()
    client.login(user)
    response = client.get(reverse('auth:logout'),
                           {'next': "/abc"})
    assert response.status_code == 302
    assert response.url == "/abc"


@pytest.mark.django_db
def test_yandex_login_from_email(client):
    """
    yandex_login can be exctracted from email if email is on @yandex.ru
    """
    branch = BranchFactory()
    user = User.objects.create_user("testuser1", "foo@bar.net",
                                    "test123foobar@!", branch=branch)
    assert not user.yandex_login
    user = User.objects.create_user("testuser2", "foo@yandex.ru",
                                    "test123foobar@!", branch=branch)
    assert user.yandex_login == "foo"


@pytest.mark.django_db
def test_short_bio(client):
    """
    `get_short_bio` split bio on the first paragraph
    """
    user = UserFactory()
    user.bio = "Some small text"
    assert user.get_short_bio() == "Some small text"
    user.bio = """Some large text.

    It has several paragraphs, by the way."""
    assert user.get_short_bio() == "Some large text."


@pytest.mark.django_db
def test_graduate_can_edit_testimonial(client):
    """
    Only graduates can (and should) have "CSC review" field in their
    profiles
    """
    test_review = "CSC are the bollocks"
    form_data = {'testimonial': test_review}
    user = UserFactory()
    client.login(user)
    response = client.post(user.get_update_profile_url(), form_data)
    assert response.status_code == 302
    assert response.url == user.get_absolute_url()
    response = client.get(user.get_absolute_url())
    assert smart_bytes(test_review) not in response.content
    add_user_groups(user, [Roles.GRADUATE])
    user.save()
    GraduateProfileFactory(student=user)
    response = client.post(user.get_update_profile_url(), form_data)
    assert response.status_code == 302
    assert response.url == user.get_absolute_url()
    response = client.get(user.get_absolute_url())
    assert smart_bytes(test_review) in response.content


@pytest.mark.django_db
def test_duplicate_check(client):
    """
    It should be impossible to create users with equal names
    """
    user = UserFactory()
    branch = BranchFactory()
    form_data = {'username': user.username,
                 'email': user.email,
                 'gender': GenderTypes.MALE,
                 'branch': branch.pk,
                 'password1': "test123foobar@!",
                 'password2': "test123foobar@!"}
    form = UserCreationForm(data=form_data)
    assert not form.is_valid()
    new_user = UserFactory.build()
    form_data.update({
        'username': new_user.username,
        'email': new_user.email
    })
    form = UserCreationForm(data=form_data)
    assert form.is_valid()


@pytest.mark.django_db
def test_email_on_detail(client):
    """Email field should be displayed only to curators (superuser)"""
    student_mail = "student@student.mail"
    student = StudentFactory(email=student_mail)
    client.login(student)
    url = student.get_absolute_url()
    response = client.get(url)
    assert smart_bytes(student_mail) not in response.content
    # check with curator credentials
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(url)
    assert smart_bytes(student_mail) in response.content


@pytest.mark.django_db
def test_auth_restrictions(client, assert_login_redirect):
    user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
    user_data["branch"] = BranchFactory()
    user = User.objects.create_user(**user_data)
    teaching_assignments_url = reverse('teaching:assignment_list')
    assert_login_redirect(teaching_assignments_url)
    response = client.post(reverse('auth:login'), user_data)
    assert response.status_code == 200
    branch_spb = Branch.objects.get_by_natural_key(Branches.SPB, settings.SITE_ID)
    student = StudentFactory(branch=branch_spb)
    auth_data = {'username': student.username, 'password': student.raw_password}
    response = client.post(reverse('auth:login'), auth_data)
    assert response.status_code == 302
    assert client.get(teaching_assignments_url).status_code == 403
    add_user_groups(student, [Roles.TEACHER])
    response = client.get(teaching_assignments_url)
    # Teacher has no course offerings and will be redirected to the course list
    assert response.status_code == 302
    CourseFactory(teachers=[student])
    response = client.get(teaching_assignments_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_detail_view(client):
    user = UserFactory()
    response = client.get(user.get_absolute_url())
    assert response.status_code == 404
    student = StudentFactory()
    response = client.get(student.get_absolute_url())
    assert response.status_code == 200
    assert response.context['profile_user'] == student
    assert not response.context['is_editing_allowed']


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
def test_user_detail_view_should_show_online_courses_for_student(client):
    """
    Student should see his/her online courses
    """
    student = StudentFactory()
    oc = OnlineCourseRecordFactory(student=student)
    client.login(student)
    response = client.get(student.get_absolute_url())
    assert smart_bytes(oc.name) in response.content


@pytest.mark.django_db
def test_user_detail_view_should_show_online_courses_for_curators(client):
    """
    Curators should see online courses that students have passed
    """
    student = StudentFactory()
    curator = CuratorFactory()
    oc = OnlineCourseRecordFactory(student=student)
    client.login(curator)
    response = client.get(student.get_absolute_url())
    assert smart_bytes(oc.name) in response.content


@pytest.mark.django_db
def test_user_detail_view_should_not_show_online_courses_for_other_people(client):
    """
    People except student and curators should not see online courses of the student
    """
    student = StudentFactory()
    user = UserFactory()
    oc = OnlineCourseRecordFactory(student=student)
    response = client.get(student.get_absolute_url())
    # Unauthenticated users
    assert smart_bytes(oc.name) not in response.content
    # Other users without curator permissions
    client.login(user)
    assert smart_bytes(oc.name) not in response.content


@pytest.mark.django_db
def test_user_detail_view_should_show_links_for_online_courses(client):
    """
    Test that online course name is shown as an <a> link with correct href
    """
    student = StudentFactory()
    oc = OnlineCourseRecordFactory(student=student,
                                   url="http://course-page.org")
    client.login(student)
    response = client.get(student.get_absolute_url())
    soup = BeautifulSoup(response.content, 'html.parser')
    links = soup.find_all(href=oc.url)
    assert len(links) == 1
    assert oc.name == links[0].text


@pytest.mark.django_db
def test_student_should_have_profile(client):
    client.login(CuratorFactory())
    user = UserFactory(photo='/a/b/c')
    assert user.groups.count() == 0
    form_data = {k: v for k, v in model_to_dict(user).items() if v is not None}
    del form_data['photo']
    form_data.update({
        # Django wants all inline formsets
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
    response = client.post(admin_url, form_data)
    assert response.status_code == 200

    def get_user_group_formset(response):
        form = None
        for inline_formset_obj in response.context['inline_admin_formsets']:
            if issubclass(inline_formset_obj.formset.model, UserGroup):
                form = inline_formset_obj.formset
        assert form, "Inline form for UserGroup is missing"
        return form
    user_group_form = get_user_group_formset(response)
    assert not user_group_form.is_valid()
    StudentProfileFactory(user=user)
    UserGroup.objects.filter(user=user).delete()
    response = client.post(admin_url, form_data)
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.groups.count() == 1
