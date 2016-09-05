import pytest

from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.test.client import Client
from pytest_django.lazy_django import skip_if_no_django

from core.models import City
from learning.settings import PARTICIPANT_GROUPS
from users.factories import UserFactory, StudentFactory, StudentClubFactory, \
    TeacherCenterFactory, StudentCenterFactory

CENTER_SITE_ID = 1
CLUB_SITE_ID = 2


def pytest_report_header(config):
    return "Run py.test --ds=csclub.settings.test cscsite/csclub/ for " \
           "club site specific tests. I's impossible to change django " \
           "settings with pytest.ini and not loose this conftest.py"


class CustomDjangoTestClient(Client):
    """ Add some utility methods to Django test client """
    def login(self, user_model):
        return super(CustomDjangoTestClient, self).login(
            username=user_model.username, password=user_model.raw_password)


@pytest.fixture()
def client():
    """Override Django test client instance."""
    skip_if_no_django()
    return CustomDjangoTestClient()


@pytest.fixture(scope="session")
def user_factory():
    return UserFactory

# FIXME: avoid this fixture and try to delete it in the future
@pytest.fixture(scope="session")
def student_factory():
    """Both club and center groups"""
    return StudentFactory

# FIXME: avoid this fixture and try to delete it in the future
@pytest.fixture(scope="session")
def student_center_factory():
    return StudentCenterFactory


# FIXME: avoid this fixture and try to delete it in the future
@pytest.fixture(scope="session")
def student_club_factory():
    return StudentClubFactory

# FIXME: avoid this fixture and try to delete it in the future
@pytest.fixture(scope="session")
def teacher_center_factory():
    return TeacherCenterFactory


@pytest.fixture(scope="session", autouse=True)
def replace_django_data_migrations_with_pytest_fixture(django_db_setup,
                                                       django_db_blocker):
    """Django data migrations with py.test due to tests runs with --nomigrations
    """
    with django_db_blocker.unblock():
        # Create user groups
        for group_id, group_name in PARTICIPANT_GROUPS:
            Group.objects.update_or_create(
                pk=group_id,
                defaults={
                    "name": group_name
                }
            )

        # Create sites
        Site.objects.update_or_create(
            id=CENTER_SITE_ID,
            defaults={
                "domain": "compscicenter.ru",
                "name": "compscicenter.ru"
            }
        )
        Site.objects.update_or_create(
            id=CLUB_SITE_ID,
            defaults={
                "domain": "compsciclub.ru",
                "name": "compsciclub.ru"
            }
        )

        # Create cities
        City.objects.update_or_create(
            code="RU SPB",
            defaults={
                "name": "Saint Petersburg"
            }
        )

        City.objects.update_or_create(
            code="RU KZN",
            defaults={
                "name": "Kazan"
            }
        )


@pytest.fixture(scope="function")
def curator(user_factory):
    return user_factory.create(is_superuser=True, is_staff=True)


