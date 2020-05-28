from urllib.parse import urlparse

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import resolve
from post_office.models import EmailTemplate
from pytest_django.lazy_django import skip_if_no_django

from core.tests.factories import BranchFactory, CityFactory
from core.tests.utils import TestClient, CSCTestCase
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
        Site.objects.all().delete()
        domains = [
            (settings.TEST_DOMAIN_ID, settings.TEST_DOMAIN),
            (settings.ANOTHER_DOMAIN_ID, settings.ANOTHER_DOMAIN),
        ]
        for site_id, domain in domains:
            Site.objects.update_or_create(id=site_id, defaults={
                "domain": domain,
                "name": domain
            })
        from django.db import connection
        from django.core.management.color import no_style
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), [Site])
        with connection.cursor() as cursor:
            for sql in sequence_sql:
                cursor.execute(sql)
        # Create cities
        city_spb = CityFactory(name="Saint Petersburg", code="spb", abbr="spb")
        city_nsk = CityFactory(name="Novosibirsk", code="nsk", abbr="nsk",
                               time_zone='Asia/Novosibirsk',)
        city_kzn = CityFactory(name="Kazan", code="kzn", abbr="kzn")
        # FIXME: add ru/en names
        for site_id in (settings.TEST_DOMAIN_ID, settings.ANOTHER_DOMAIN_ID):
            BranchFactory(code=Branches.SPB,
                          site=Site.objects.get(id=site_id),
                          name="Санкт-Петербург",
                          name_ru="Санкт-Петербург",
                          name_en="Saint Petersburg",
                          city=city_spb)
            BranchFactory(code=Branches.NSK,
                          site=Site.objects.get(id=site_id),
                          name="Новосибирск",
                          name_ru="Новосибирск",
                          name_en="Novosibirsk",
                          time_zone='Asia/Novosibirsk',
                          city=city_nsk)

        BranchFactory(code=Branches.DISTANCE,
                      site=Site.objects.get(id=settings.TEST_DOMAIN_ID),
                      name="Заочное",
                      city=None)

        BranchFactory(code='kzn',
                      site=Site.objects.get(id=settings.ANOTHER_DOMAIN_ID),
                      name="Казань",
                      city=city_kzn)

        from notifications import NotificationTypes
        for t in NotificationTypes:
            Type.objects.update_or_create(
                id=t.value,
                defaults={
                    "code": t.name
                }
            )

        if apps.is_installed('admission'):
            # Create email templates
            from admission.constants import INTERVIEW_FEEDBACK_TEMPLATE, \
                APPOINTMENT_INVITATION_TEMPLATE
            template_names = (
                APPOINTMENT_INVITATION_TEMPLATE,
                INTERVIEW_FEEDBACK_TEMPLATE,
            )
            for template_name in template_names:
                EmailTemplate.objects.update_or_create(
                    name=template_name
                )
