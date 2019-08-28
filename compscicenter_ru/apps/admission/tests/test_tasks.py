import pytest
from post_office.models import Email

from admission.models import Contest
from admission.tasks import register_in_yandex_contest
from admission.tests.factories import ApplicantFactory, ContestFactory, \
    CampaignFactory


@pytest.mark.django_db
def test_register_in_yandex_contest_success(mocker):
    """Email has been generated after registration in yandex contest"""
    mocked_api = mocker.patch('api.providers.yandex_contest.YandexContestAPI.register_in_contest')
    mocked_api.return_value = 200, 1
    campaign = CampaignFactory()
    contest = ContestFactory(campaign=campaign, type=Contest.TYPE_TEST)
    applicant = ApplicantFactory(campaign=campaign, yandex_login=None)
    with pytest.raises(AttributeError) as exc:
        register_in_yandex_contest(applicant.id, language_code='ru')
    assert "Empty yandex id" in str(exc.value)
    applicant.yandex_login = 'fakeYandexID'
    applicant.save()
    assert Email.objects.count() == 0
    register_in_yandex_contest(applicant.id, language_code='ru')
    assert Email.objects.count() == 1
