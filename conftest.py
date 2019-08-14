from urllib.parse import urlparse

import pytest
from django.contrib.sites.models import Site
from django.urls import resolve
from post_office.models import EmailTemplate
from pytest_django.lazy_django import skip_if_no_django

from admission.constants import INTERVIEW_REMINDER_TEMPLATE, \
    INTERVIEW_FEEDBACK_TEMPLATE, APPOINTMENT_INVITATION_TEMPLATE
from core.models import City, Branch
from core.tests.factories import BranchFactory
from core.tests.utils import TestClient, TEST_DOMAIN, CSCTestCase, \
    ANOTHER_DOMAIN, TEST_DOMAIN_ID, ANOTHER_DOMAIN_ID
from learning.settings import Branches
from notifications.models import Type
from users.tests.factories import CuratorFactory


@pytest.fixture()
def client():
    """Customize login method for Django test client."""
    skip_if_no_django()
    return TestClient()


@pytest.fixture(scope="session")
def assert_redirect():
    """Uses customized TestCase.assertRedirects as a comparing tool."""
    _TC = CSCTestCase()

    def wrapper(*args, **kwargs):
        return _TC.assertRedirects(*args, **kwargs)

    return wrapper


@pytest.fixture(scope="function")
def assert_login_redirect(client, settings, assert_redirect):
    def wrapper(url, form=None, **kwargs):
        method_name = kwargs.pop("method", "get")
        client_method = getattr(client, method_name)
        # Cast `next` value to the relative path since
        # after successful login we redirect to the same domain.
        path = urlparse(url).path
        expected_path = "{}?next={}".format(settings.LOGIN_URL, path)
        assert_redirect(client_method(url, form, **kwargs), expected_path)
    return wrapper


@pytest.fixture(scope="function")
def curator():
    # Sequences are resetting for each test, don't rely on there values here
    return CuratorFactory(email='curators@test.ru',
                          first_name='Global',
                          username='curator',
                          last_name='Curator')


@pytest.fixture(scope="function")
def lms_resolver(settings):
    def wrapper(url):
        rel_url = urlparse(url).path
        lms_urlconf = settings.SUBDOMAIN_URLCONFS[settings.LMS_SUBDOMAIN]
        return resolve(rel_url, urlconf=lms_urlconf)
    return wrapper


@pytest.fixture(scope="session", autouse=True)
def _prepopulate_db_with_data(django_db_setup, django_db_blocker):
    """
    Populates test database with missing data required for tests.

    To simplify db management migrations could be recreated from the scratch
    without already applied data migrations. Restore these data in one place
    since some tests rely on it.
    """
    with django_db_blocker.unblock():
        # Create site objects with respect to AutoField
        domains = [
            (TEST_DOMAIN_ID, TEST_DOMAIN),
            (ANOTHER_DOMAIN_ID, ANOTHER_DOMAIN),
        ]
        for site_id, domain in domains:
            try:
                site = Site.objects.get(id=site_id)
                site.domain = domain
                site.name = domain
                site.save()
            except Site.DoesNotExist:
                site = Site(domain=domain, name=domain)
                site.save()
                site.id = site_id
                site.save()

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

        BranchFactory(code=Branches.SPB,
                      site=Site.objects.get(id=TEST_DOMAIN_ID),
                      name="Санкт-Петербург",
                      is_remote=False)

        BranchFactory(code=Branches.NSK,
                      site=Site.objects.get(id=TEST_DOMAIN_ID),
                      name="Новосибирск",
                      time_zone='Asia/Novosibirsk',
                      is_remote=False)

        BranchFactory(code=Branches.DISTANCE,
                      site=Site.objects.get(id=TEST_DOMAIN_ID),
                      name="Заочное",
                      is_remote=True)

        from notifications import NotificationTypes
        for t in NotificationTypes:
            Type.objects.update_or_create(
                id=t.value,
                defaults={
                    "code": t.name
                }
            )

        # Create email templates

        template_names = (
            APPOINTMENT_INVITATION_TEMPLATE,
            INTERVIEW_FEEDBACK_TEMPLATE,
            INTERVIEW_REMINDER_TEMPLATE,
        )
        for template_name in template_names:
            EmailTemplate.objects.update_or_create(
                name=template_name
            )
