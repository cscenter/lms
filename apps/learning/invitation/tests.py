import datetime

import pytest

from django.contrib.sites.models import Site
from django.utils.timezone import now

from auth.tasks import ActivationEmailContext
from core.tests.factories import SiteFactory, BranchFactory
from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.invitation.forms import InvitationRegistrationForm, CompleteAccountForm
from learning.invitation.views import (
    InvitationURLParamsMixin, complete_student_profile, is_student_profile_valid
)
from learning.tests.factories import CourseInvitationFactory
from users.constants import GenderTypes, Roles
from users.models import User, StudentTypes
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
    site = SiteFactory(id=settings.SITE_ID)
    branch = BranchFactory(site=site)
    user = UserFactory(branch=branch)
    client.login(user)
    response = client.get(url)
    assert not is_student_profile_valid(user, site)
    assert response.status_code == 302

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
    branch = BranchFactory()
    course_invitation = CourseInvitationFactory(invitation__branches=[branch])
    form = InvitationRegistrationForm(data={}, invitation=course_invitation.invitation)
    assert not form.is_valid()
    missing_fields = ["email", "branch", "last_name", "first_name", "gender", "telegram_username",
                      "birth_date", "password1", "password2", "captcha"]
    assert set(form.errors) == set(missing_fields)
    form_data = {
        'email': 'test@test.com',
        'branch': BranchFactory(),
        'last_name': 'Last Name',
        'first_name': 'First Name',
        'gender': 'helicopter',
        'telegram_username': '@telegram',
        'birth_date': '100-03-999',
        'password1': '123123',
        'password2': '123123',
        'g-recaptcha-response': 'PASSED'
    }
    form = InvitationRegistrationForm(data=form_data, invitation=course_invitation.invitation)
    assert not form.is_valid()
    wrong_fields = ["branch", "birth_date", "gender"]
    assert set(form.errors) == set(wrong_fields)
    form_data['birth_date'] = datetime.date(2000, 1, 1)
    form_data['branch'] = branch
    form_data['gender'] = GenderTypes.MALE
    form = InvitationRegistrationForm(data=form_data, invitation=course_invitation.invitation)
    assert form.is_valid()@pytest.mark.django_db

@pytest.mark.django_db
def test_complete_account_form(client, mocker):
    mocked_recaptcha_response = mocker.patch("captcha.client.recaptcha_request")
    read_mock = mocker.MagicMock()
    read_mock.read.return_value = b'{"success": true, "challenge_ts":' \
        b'"2019-01-11T13:57:23Z", "hostname": "testkey.google.com"}'
    mocked_recaptcha_response.return_value = read_mock
    branch = BranchFactory()
    course_invitation = CourseInvitationFactory(invitation__branches=[branch])
    user = UserFactory()
    form = CompleteAccountForm(data={}, invitation=course_invitation.invitation, instance=user)
    assert not form.is_valid()
    missing_fields = ["branch", "first_name", "last_name"]
    assert set(form.errors) == set(missing_fields)
    form_data = {
        'branch': BranchFactory(),
        'last_name': 'Last Name',
        'first_name': 'First Name'
    }
    form = CompleteAccountForm(data=form_data, invitation=course_invitation.invitation, instance=user)
    assert not form.is_valid()
    wrong_fields = ["branch"]
    assert set(form.errors) == set(wrong_fields)
    form_data['branch'] = branch
    form = CompleteAccountForm(data=form_data, invitation=course_invitation.invitation, instance=user)
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
    branch = BranchFactory()
    course_invitation = CourseInvitationFactory(course__semester=current_term, invitation__branches=[branch])
    invitation = course_invitation.invitation
    register_url = reverse("invitation:registration",
                           kwargs={"token": invitation.token},
                           subdomain=settings.LMS_SUBDOMAIN)
    test_email = 'test@test.com'
    assert not User.objects.filter(email=test_email).exists()
    form_data = {
        'email': test_email,
        'branch': branch.id,
        'last_name': 'Last Name',
        'first_name': 'First Name',
        'gender': GenderTypes.MALE,
        'telegram_username': '@telegram',
        'birth_date': datetime.date(2000, 1, 1),
        'password1': '123123',
        'password2': '123123',
        'g-recaptcha-response': 'PASSED'
    }
    form = InvitationRegistrationForm(data=form_data, invitation=invitation)
    assert form.is_valid(), form.errors
    response = client.post(register_url, form_data)
    assert response.status_code == 302
    reg_complete_url = reverse("invitation:registration_complete",
                               subdomain=settings.LMS_SUBDOMAIN)
    assert_redirect(response, reg_complete_url)
    assert User.objects.filter(email=test_email).exists()
    new_user = User.objects.get(email=test_email)
    assert not new_user.is_active
    assert new_user.branch == branch
    assert new_user.telegram_username == "telegram"
    assert new_user.birth_date == datetime.date(2000, 1, 1)
    assert new_user.last_name == 'Last Name'
    assert Roles.INVITED in new_user.roles
    assert new_user.gave_permission_at is None
    student_profile = new_user.get_student_profile(site=new_user.branch.site)
    assert student_profile
    assert student_profile.year_of_admission == invitation.semester.academic_year
    assert student_profile.branch in invitation.branches.all()
    assert student_profile.branch == new_user.branch
    assert student_profile.type == StudentTypes.INVITED
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
