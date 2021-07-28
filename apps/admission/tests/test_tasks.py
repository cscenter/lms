import pytest
from post_office.models import Email

from admission.constants import ContestTypes
from admission.models import Contest, YandexContestImportResults
from admission.tasks import import_campaign_contest_results, register_in_yandex_contest
from admission.tests.factories import ApplicantFactory, CampaignFactory, ContestFactory
from core.urls import reverse
from tasks.models import Task
from users.tests.factories import CuratorFactory


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
def test_import_contest_result(client, mocker):
    mocked_api = mocker.patch('admission.models.YandexContestIntegration.import_results')
    scoreboard_total = 10
    updated_total = 1
    mocked_api.return_value = YandexContestImportResults(on_scoreboard=scoreboard_total,
                                                         updated=updated_total)
    curator = CuratorFactory()
    client.login(curator)
    campaign = CampaignFactory()

    url = reverse('admission:import_testing_results', kwargs={'campaign_id': campaign.id, 
                                                              'contest_type': ContestTypes.TEST})
    response = client.post(url)
    assert response.status_code == 201
    task_name = "admission.tasks.import_testing_results"
    latest_task = (Task.objects
                   .get_task(task_name, kwargs={"campaign_id": campaign.id,
                                                "contest_type": ContestTypes.TEST})
                   .order_by("-id")
                   .first())
    assert latest_task.is_completed
