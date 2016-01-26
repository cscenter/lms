from functools import partial

import pytest
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.test.client import Client
from pytest_django.lazy_django import skip_if_no_django

from core.models import City
from learning.settings import PARTICIPANT_GROUPS
from users.factories import UserFactory, StudentFactory, StudentClubFactory, \
    TeacherFactory

CENTER_SITE_ID = 1
CLUB_SITE_ID = 2


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

@pytest.fixture(scope="session")
def student_factory():
    return StudentFactory

@pytest.fixture(scope="session")
def student_club_factory():
    return StudentClubFactory

@pytest.fixture(scope="session")
def teacher_factory():
    return TeacherFactory


@pytest.fixture(scope="session", autouse=True)
def replace_django_data_migrations_with_pytest_fixture(_django_db_setup,
                                                       _django_cursor_wrapper):
    """Django data migrations with py.test due to tests runs with --nomigrations"""
    with _django_cursor_wrapper:
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
def curator(user_factory_cls):
    return user_factory_cls.create(is_superuser=True, is_staff=True)


