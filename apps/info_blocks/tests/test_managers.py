import pytest

from info_blocks.models import CurrentInfoBlockTags, InfoBlock
from info_blocks.tests.factories import InfoBlockFactory


@pytest.mark.django_db
def test_info_blocks_manager_for_site(settings):
    u1, u2 = InfoBlockFactory.create_batch(2, site__domain=settings.TEST_DOMAIN)
    u3 = InfoBlockFactory(site__domain=settings.ANOTHER_DOMAIN)

    infoblocks_test = list(InfoBlock.objects.for_site(settings.TEST_DOMAIN_ID))
    assert len(infoblocks_test) == 2
    assert u1 in infoblocks_test
    assert u2 in infoblocks_test


@pytest.mark.django_db
def test_info_blocks_manager_with_tag():
    u1, u2 = InfoBlockFactory.create_batch(2, tags=[CurrentInfoBlockTags.USEFUL])
    u3 = InfoBlockFactory(tags=[CurrentInfoBlockTags.HONOR_CODE])

    infoblocks_useful = list(InfoBlock.objects.with_tag(CurrentInfoBlockTags.USEFUL))
    assert len(infoblocks_useful) == 2
    assert u1 in infoblocks_useful
    assert u2 in infoblocks_useful