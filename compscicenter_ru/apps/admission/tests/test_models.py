import pytest

from admission.tests.factories import CampaignFactory, ContestFactory, \
    ApplicantFactory
from admission.models import Contest


# FIXME: Test.compute_contest_id instead

@pytest.mark.django_db
def test_applicant_set_contest_id(client):
    """Test contest id rotation for testing stage"""
    campaign = CampaignFactory.create()
    contests = ContestFactory.create_batch(3, campaign=campaign,
                                           type=Contest.TYPE_TEST)
    c1, c2, c3 = sorted(contests, key=lambda x: x.contest_id)
    ContestFactory(campaign=campaign, type=Contest.TYPE_EXAM)
    a = ApplicantFactory(campaign=campaign)
    expected_index = a.id % 3
    assert a.online_test.yandex_contest_id == contests[expected_index].contest_id
    expected_contest_id = contests[expected_index].contest_id
    a = ApplicantFactory(campaign=campaign)
    a = ApplicantFactory(campaign=campaign)
    a = ApplicantFactory(campaign=campaign)
    # At this point we made full cycle over all available contests and should
    # repeat them due to round robin
    assert a.online_test.yandex_contest_id == expected_contest_id
