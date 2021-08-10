import pytest
from post_office.models import Email

from admission.constants import ContestTypes
from admission.models import Contest, YandexContestImportResults
from admission.services import (
    create_contest_results_import_task, get_latest_contest_results_task
)
from admission.tasks import import_campaign_contest_results, register_in_yandex_contest
from admission.tests.factories import ApplicantFactory, CampaignFactory, ContestFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_register_in_yandex_contest_success(mocker):
    """Email has been generated after registration in yandex contest"""
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.register_in_contest')
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


@pytest.mark.django_db
def test_import_contest_scores(client, mocker):
    mocked = mocker.patch('admission.models.YandexContestIntegration.import_scores')
    mocked.return_value = YandexContestImportResults(on_scoreboard=10, updated=1)
    campaign = CampaignFactory(current=True)
    contest_testing = ContestFactory(campaign=campaign, type=ContestTypes.TEST)
    contest_exam = ContestFactory(campaign=campaign, type=ContestTypes.EXAM)
    task = create_contest_results_import_task(campaign.pk, ContestTypes.TEST, author=UserFactory())
    import_campaign_contest_results(task_id=task.pk)
    latest_task = get_latest_contest_results_task(campaign, ContestTypes.TEST)
    assert latest_task.is_completed
    mocked.assert_called_once()
    _, call_kwargs = mocked.call_args
    assert call_kwargs['contest'] == contest_testing

