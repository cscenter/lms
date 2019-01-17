import pytest
from django.conf import settings

from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from post_office.models import EmailTemplate

from notifications.models import Type
from django.test.client import Client
from pytest_django.lazy_django import skip_if_no_django

from core.models import City
from users.constants import AcademicRoles
from users.factories import UserFactory


class TestClient(Client):
    def login(self, user_model):
        """
        User factory creates model with attached raw password what allows to
        authenticate user later with default backend.
        """
        return super().login(username=user_model.username,
                             password=user_model.raw_password)


@pytest.fixture()
def client():
    """Customize login method for Django test client."""
    skip_if_no_django()
    return TestClient()


@pytest.fixture(scope="session")
def assert_redirect():
    """Uses Django's SimpleTestCase.assertRedirects as comparing tool"""
    from django.test import SimpleTestCase

    _STS = SimpleTestCase()

    def wrapper(*args, **kwargs):
        return _STS.assertRedirects(*args, **kwargs)

    return wrapper


@pytest.fixture(scope="function")
def assert_login_redirect(client, settings, assert_redirect):
    def wrapper(url, form=None, **kwargs):
        method_name = kwargs.pop("method", "get")
        client_method = getattr(client, method_name)
        assert_redirect(client_method(url, form, **kwargs),
                        "{}?next={}".format(settings.LOGIN_URL, url))
    return wrapper


@pytest.fixture(scope="function")
def curator():
    return UserFactory.create(is_superuser=True, is_staff=True)


@pytest.fixture(scope="session", autouse=True)
def _prepopulate_db_with_data(django_db_setup, django_db_blocker):
    """
    Populates test database with missing data required for tests.

    To simplify db management migrations could be recreated from the scratch
    without already applied data migrations. Restore these data in one place
    since some tests rely on it.
    """
    with django_db_blocker.unblock():
        # Create user groups
        for group_id, group_name in AcademicRoles.values.items():
            Group.objects.update_or_create(
                pk=group_id,
                defaults={
                    "name": group_name
                }
            )

        # Create sites
        Site.objects.update_or_create(
            id=settings.CENTER_SITE_ID,
            defaults={
                "domain": "compscicenter.ru",
                "name": "compscicenter.ru"
            }
        )
        Site.objects.update_or_create(
            id=settings.CLUB_SITE_ID,
            defaults={
                "domain": "compsciclub.ru",
                "name": "compsciclub.ru"
            }
        )

        # Create cities
        City.objects.update_or_create(
            code="spb",
            defaults={
                "name": "Saint Petersburg",
                "abbr": "spb"
            }
        )

        City.objects.update_or_create(
            code="kzn",
            defaults={
                "name": "Kazan",
                "abbr": "kzn"
            }
        )

        City.objects.update_or_create(
            code="nsk",
            defaults={
                "name": "Novosibirsk",
                "abbr": "nsk"
            }
        )

        from notifications import types
        for t in types:
            Type.objects.update_or_create(
                id=t.value,
                defaults={
                    "code": t.name
                }
            )

        # Create email templates
        from admission.models import Interview, InterviewInvitation

        template_names = [
            Interview.FEEDBACK_TEMPLATE,
            Interview.REMINDER_TEMPLATE,
            InterviewInvitation.ONE_STREAM_EMAIL_TEMPLATE,
            "admission-interview-invitation-n-streams"
        ]
        for template_name in template_names:
            EmailTemplate.objects.update_or_create(
                name=template_name
            )
