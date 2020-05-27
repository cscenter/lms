import pytest

from useful.models import CurrentUsefulTags, Useful
from useful.tests.factories import UsefulFactory


@pytest.mark.django_db
def test_useful_manager_for_site(settings):
    u1, u2 = UsefulFactory.create_batch(2, site__domain=settings.TEST_DOMAIN)
    u3 = UsefulFactory(site__domain=settings.ANOTHER_DOMAIN)

    useful_test = list(Useful.objects.for_site(settings.TEST_DOMAIN_ID))
    assert len(useful_test) == 2
    assert u1 in useful_test
    assert u2 in useful_test


@pytest.mark.django_db
def test_useful_manager_with_tag():
    u1, u2 = UsefulFactory.create_batch(2, tags=[CurrentUsefulTags.USEFUL])
    u3 = UsefulFactory(tags=[CurrentUsefulTags.HONOR_CODE])

    useful_test = list(Useful.objects.with_tag(CurrentUsefulTags.USEFUL))
    assert len(useful_test) == 2
    assert u1 in useful_test
    assert u2 in useful_test