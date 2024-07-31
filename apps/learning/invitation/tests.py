import datetime

import pytest

from django.contrib.sites.models import Site
from django.utils.timezone import now

from auth.tasks import ActivationEmailContext
from core.tests.factories import SiteFactory
from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.invitation.forms import InvitationRegistrationForm
from learning.invitation.views import (
    InvitationURLParamsMixin, complete_student_profile, is_student_profile_valid
)
from learning.tests.factories import CourseInvitationFactory
from users.constants import GenderTypes, Roles
from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_invitation_view(client, lms_resolver, assert_redirect, settings):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    course_invitation = CourseInvitationFactory(course__semester=current_term)
    invitation = course_invitation.invitation
    url = invitation.get_absolute_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, InvitationURLParamsMixin)
    assert invitation.is_active
    response = client.get(url)
    assert response.status_code == 302
    login_url = reverse("invitation:login",
                        kwargs={"token": invitation.token},
                        subdomain=settings.LMS_SUBDOMAIN)
    assert_redirect(response, login_url)
    user = UserFactory()
    client.login(user)
    response = client.get(url)
    site = SiteFactory(id=settings.SITE_ID)
    assert not is_student_profile_valid(user, site, invitation)
    assert response.status_code == 302
    # FIXME check url to complete profile view
    complete_student_profile(user, site, invitation)
    response = client.get(url)
    assert response.status_code == 200
    assert 'invitation' in response.context_data
    assert response.context_data['invitation'] == invitation
    # Make sure we select courses for target invitation only
    CourseInvitationFactory()
    response = client.get(url)
    assert len(response.context_data['invitation_course_list']) == 1
    assert response.context_data['invitation_course_list'][0] == course_invitation


@pytest.mark.django_db
def test_invitation_register_form(client, mocker):
    mocked_recaptcha_response = mocker.patch("captcha.client.recaptcha_request")
    read_mock = mocker.MagicMock()
    read_mock.read.return_value = b'{"success": true, "challenge_ts":' \
        b'"2019-01-11T13:57:23Z", "hostname": "testkey.google.com"}'
    mocked_recaptcha_response.return_value = read_mock
    assert not User.objects.filter(email='test@test.com').exists()
    form_data = {
        'email': 'test@test.com',
        'last_name': 'Last Name',
        'first_name': 'First Name',
        'gender': GenderTypes.MALE,
        'password1': '123123',
        'password2': '123123',
        'g-recaptcha-response': 'PASSED'
    }
    form = InvitationRegistrationForm(data=form_data)
    assert form.is_valid()


@pytest.mark.django_db
def test_invitation_register_view(client, assert_redirect, settings, mocker):
    mocked_task = mocker.patch('learning.invitation.views.send_activation_email')
    mocked_recaptcha_response = mocker.patch("captcha.client.recaptcha_request")
    read_mock = mocker.MagicMock()
    read_mock.read.return_value = b'{"success": true, "challenge_ts":' \
        b'"2019-01-11T13:57:23Z", "hostname": "testkey.google.com"}'
    mocked_recaptcha_response.return_value = read_mock
    settings.LANGUAGE_CODE = 'ru'
    future = (now() + datetime.timedelta(days=3)).date()
    current_term = SemesterFactory.create_current(enrollment_period__ends_on=future)
    course_invitation = CourseInvitationFactory(course__semester=current_term)
    invitation = course_invitation.invitation
    register_url = reverse("invitation:registration",
                           kwargs={"token": invitation.token},
                           subdomain=settings.LMS_SUBDOMAIN)
    test_email = 'test@test.com'
    assert not User.objects.filter(email=test_email).exists()
    form_data = {
        'email': test_email,
        'last_name': 'Last Name',
        'first_name': 'First Name',
        'gender': GenderTypes.MALE,
        'password1': '123123',
        'password2': '123123',
        'g-recaptcha-response': 'PASSED'
    }
    form = InvitationRegistrationForm(data=form_data)
    assert form.is_valid()
    response = client.post(register_url, form_data)
    assert response.status_code == 302
    reg_complete_url = reverse("invitation:registration_complete",
                               subdomain=settings.LMS_SUBDOMAIN)
    assert_redirect(response, reg_complete_url)
    assert User.objects.filter(email=test_email).exists()
    new_user = User.objects.get(email=test_email)
    assert not new_user.is_active
    assert new_user.last_name == 'Last Name'
    assert Roles.INVITED in new_user.roles
    assert new_user.gave_permission_at is None
    student_profile = new_user.get_student_profile(site=invitation.branch.site)
    assert student_profile
    assert student_profile.year_of_admission == invitation.semester.academic_year
    assert student_profile.branch == invitation.branch
    assert mocked_task.delay.called
    called_args, called_kwargs = mocked_task.delay.call_args
    email_context, reg_profile_id = called_args
    assert reg_profile_id == new_user.registrationprofile.pk
    abs_url = client.get('', secure=False).wsgi_request.build_absolute_uri
    activation_url = reverse("invitation:activate", kwargs={
        "token": invitation.token,
        "activation_key": new_user.registrationprofile.activation_key
    }, subdomain=settings.LMS_SUBDOMAIN)
    site = Site.objects.get_current()
    assert email_context == ActivationEmailContext(
            site_name=site.name,
            activation_url=abs_url(activation_url),
            language_code=settings.LANGUAGE_CODE)


@pytest.mark.django_db
def test_invitation_view_enrolled_students_log(client, lms_resolver, assert_redirect, settings):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    course_invitation = CourseInvitationFactory(course__semester=current_term)
    invitation = course_invitation.invitation
    url = invitation.get_absolute_url()
    client.get(url)
    # Anonymous user working
    assert not invitation.enrolled_students.count()

    user = UserFactory()
    client.login(user)
    client.get(url)
    # User without profile should register profile
    assert not invitation.enrolled_students.count()

    site = SiteFactory(id=settings.SITE_ID)
    complete_student_profile(user, site, invitation)
    response = client.get(url)
    assert response.status_code == 200
    # User with completed profile should be added to enrolled_students set
    assert invitation.enrolled_students.count() == 1

    response = client.get(url)
    assert response.status_code == 200
    # There should be no double entry
    assert invitation.enrolled_students.count() == 1

    user_two = UserFactory()
    complete_student_profile(user_two, site, invitation)
    client.login(user_two)
    response = client.get(url)
    assert response.status_code == 200
    profile_one = user.get_student_profile()
    profile_two = user_two.get_student_profile()
    assert set(invitation.enrolled_students.all()) == {profile_one, profile_two}
