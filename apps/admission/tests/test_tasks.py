import pytest
from post_office.models import Email

from admission.constants import ContestTypes, ChallengeStatuses
from admission.models import Contest, YandexContestImportResults, Olympiad
from admission.services import (
    create_contest_results_import_task,
    get_latest_contest_results_task,
)
from admission.tasks import import_campaign_contest_results, register_in_yandex_contest
from admission.tests.factories import ApplicantFactory, CampaignFactory, ContestFactory, OlympiadFactory
from users.tests.factories import UserFactory
from grading.api.yandex_contest import Error as YandexContestError


@pytest.mark.django_db
def test_register_in_yandex_contest_success(mocker):
    """Email has been generated after registration in yandex contest"""
    mocked_api = mocker.patch(
        "grading.api.yandex_contest.YandexContestAPI.register_in_contest"
    )
    mocked_api.return_value = 200, 1
    campaign = CampaignFactory()
    contest = ContestFactory(campaign=campaign, type=ContestTypes.TEST)
    applicant = ApplicantFactory(campaign=campaign, yandex_login=None)
    with pytest.raises(AttributeError) as exc:
        register_in_yandex_contest(applicant.id, language_code="ru")
    assert "Empty yandex id" in str(exc.value)
    applicant.yandex_login = "fakeYandexID"
    applicant.save()
    assert Email.objects.count() == 0
    register_in_yandex_contest(applicant.id, language_code="ru")
    assert Email.objects.count() == 1


@pytest.mark.django_db
def test_import_contest_scores(client, mocker):
    mocked = mocker.patch("admission.models.YandexContestIntegration.import_scores")
    mocked.return_value = YandexContestImportResults(on_scoreboard=10, updated=1)
    campaign = CampaignFactory(current=True)
    contest_testing = ContestFactory(campaign=campaign, type=ContestTypes.TEST)
    contest_exam = ContestFactory(campaign=campaign, type=ContestTypes.EXAM)
    task = create_contest_results_import_task(
        campaign.pk, ContestTypes.TEST, author=UserFactory()
    )
    import_campaign_contest_results(task_id=task.pk)
    latest_task = get_latest_contest_results_task(campaign, ContestTypes.TEST)
    assert latest_task.is_completed
    mocked.assert_called_once()
    _, call_kwargs = mocked.call_args
    assert call_kwargs["contest"] == contest_testing


@pytest.mark.django_db
def test_olympiad_contest_integration(mocker):
    campaign = CampaignFactory()
    contest = ContestFactory(
        campaign=campaign, 
        type=ContestTypes.OLYMPIAD,
        contest_id="12345"
    )
    applicant = ApplicantFactory(
        campaign=campaign,
        yandex_login="test_user"
    )
    olympiad = OlympiadFactory(
        applicant=applicant,
        yandex_contest_id=contest.contest_id,
        status=ChallengeStatuses.REGISTERED,
        contest_participant_id=1001
    )
    
    mock_api = mocker.MagicMock()
    mock_api.standings.return_value = (200, {
        "titles": [{"name": "Task 1"}, {"name": "Task 2"}, {"name": "Task 3"}],
        "rows": [{
            "score": "8.5",
            "problemResults": [
                {"score": "3.0"}, 
                {"score": "2.5"}, 
                {"score": "3.0"}
            ],
            "participantInfo": {
                "login": "test_user",
                "id": 1001
            }
        }]
    })
    
    results = Olympiad.import_scores(
        api=mock_api,
        contest=contest
    )
    
    assert results.on_scoreboard == 1
    assert results.updated == 1
    
    olympiad.refresh_from_db()
    assert olympiad.score == 9  # round 8.5 to 9
    assert olympiad.details == {"scores": ["3.0", "2.5", "3.0"]}
    
    contest.refresh_from_db()
    assert contest.details["titles"] == ["Task 1", "Task 2", "Task 3"]


@pytest.mark.django_db
def test_olympiad_import_errors(mocker):
    campaign = CampaignFactory()
    contest = ContestFactory(
        campaign=campaign, 
        type=ContestTypes.OLYMPIAD
    )
    
    mock_api = mocker.MagicMock()
    mock_api.standings.side_effect = YandexContestError("API Error")

    with pytest.raises(YandexContestError):
        Olympiad.import_scores(
            api=mock_api,
            contest=contest
        )
    
    mock_api.standings.side_effect = None
    mock_api.standings.return_value = (200, {
        "titles": [{"name": "Task 1"}],
        "rows": [{
            "score": "invalid",
            "problemResults": [{"score": "3.0"}],
            "participantInfo": {
                "login": "test_user",
                "id": 1001
            }
        }]
    })
    
    with pytest.raises(ValueError):
        Olympiad.import_scores(
            api=mock_api,
            contest=contest
        )


@pytest.mark.django_db
def test_olympiad_contest_registration(mocker):
    campaign = CampaignFactory()
    contests = ContestFactory.create_batch(
        3, 
        campaign=campaign, 
        type=ContestTypes.OLYMPIAD
    )
    applicant = ApplicantFactory(campaign=campaign)
    
    olympiad = Olympiad(applicant=applicant)
    contest_id = olympiad.compute_contest_id(ContestTypes.OLYMPIAD)
    assert contest_id is not None
    assert contest_id in [c.contest_id for c in contests]
    
    mock_register = mocker.MagicMock()
    mock_register.register_in_contest.return_value = (200, 1001)
    
    olympiad.yandex_contest_id = contest_id
    olympiad.save()
    
    olympiad.register_in_contest(mock_register)
    
    olympiad.refresh_from_db()
    assert olympiad.status == ChallengeStatuses.REGISTERED
    assert olympiad.contest_status_code == 200
    assert olympiad.contest_participant_id == 1001


@pytest.mark.django_db
def test_olympiad_contest_integration():
    campaign = CampaignFactory()
    contest = ContestFactory(
        campaign=campaign, 
        type=ContestTypes.OLYMPIAD,
        contest_id="12345"
    )
    applicant = ApplicantFactory(campaign=campaign)
    olympiad = OlympiadFactory(
        applicant=applicant,
        yandex_contest_id=contest.contest_id
    )
    
    contests = Contest.objects.filter(contest_id=olympiad.yandex_contest_id)
    assert contests.exists()
    assert contests.first() == contest
    
    contest.contest_id = "23456"
    contest.save()
    olympiad.refresh_from_db()
    assert olympiad.yandex_contest_id == "12345" 
    
    new_applicant = ApplicantFactory(campaign=campaign)
    new_olympiad = Olympiad(applicant=new_applicant)
    new_olympiad.save()
    assert new_olympiad.yandex_contest_id == "23456"
