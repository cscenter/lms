import pytest
from django.contrib.sites.models import Site

from auth.tasks import ActivationEmailContext
from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.invitation.forms import InvitationRegistrationForm
from learning.invitation.views import InvitationURLParamsMixin
from learning.roles import Roles
from learning.tests.factories import CourseInvitationFactory
from users.constants import GenderTypes
from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_invitation_view(client, lms_resolver, assert_redirect, settings):
    term = SemesterFactory.create_current()
    course_invitation = CourseInvitationFactory(course__semester=term)
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
    assert response.status_code == 200
    assert 'view' in response.context_data
    assert hasattr(response.context_data['view'], 'invitation')
    assert response.context_data['view'].invitation == invitation


@pytest.mark.django_db
def test_invitation_register_form(client):
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
    settings.LANGUAGE_CODE = 'ru'
    term = SemesterFactory.create_current()
    course_invitation = CourseInvitationFactory(course__semester=term)
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
    assert Roles.INVITED in new_user.roles
    assert mocked_task.delay.called
    called_args, called_kwargs = mocked_task.delay.call_args
    email_context, reg_profile_id = called_args
    assert reg_profile_id == new_user.registrationprofile.pk
    activation_url = reverse("invitation:activate", kwargs={
        "token": invitation.token,
        "activation_key": new_user.registrationprofile.activation_key
    }, subdomain=settings.LMS_SUBDOMAIN)
    site = Site.objects.get_current()
    assert email_context == ActivationEmailContext(
            site_name=site.name,
            activation_url=activation_url,
            language_code=settings.LANGUAGE_CODE)
