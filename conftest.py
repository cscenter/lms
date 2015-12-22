import pytest
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site

from core.models import City
from learning.constants import PARTICIPANT_GROUPS

CENTER_SITE_ID = 1
CLUB_SITE_ID = 2


@pytest.fixture(scope="session", autouse=True)
def replace_django_group_migration_with_pytest_fixture(request, _django_db_setup,
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
