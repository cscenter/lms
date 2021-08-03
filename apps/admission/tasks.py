import logging

from django_rq import job

from django.apps import apps
from django.db.models import Q
from django.utils import timezone, translation

from admission.models import Contest, Exam, Test
from admission.services import EmailQueueService
from grading.api.yandex_contest import (
    ContestAPIError, RegisterStatus, ResponseStatus, YandexContestAPI
)

logger = logging.getLogger(__name__)


def notify_admin_bad_token(campaign_id):
    """Send message about bad auth token for Yandex.Contest API"""
    pass


@job('high')
def register_in_yandex_contest(applicant_id, language_code):
    """Register user in Yandex.Contest, then send email with summary"""
    translation.activate(language_code)
    Applicant = apps.get_model('admission', 'Applicant')
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "campaign__branch", "online_test")
                 .first())
    if not applicant.yandex_login:
        logger.error(f"Empty yandex login for applicant id = {applicant_id}")
        raise AttributeError("Empty yandex id")
    online_test = applicant.online_test
    if not online_test.yandex_contest_id:  # Can't imagine when it's possible
        logger.error(f"No contest assigned to applicant id = {applicant_id}")
        raise AttributeError("Empty contest id")
    campaign = applicant.campaign
    api = YandexContestAPI(access_token=campaign.access_token,
                           refresh_token=campaign.refresh_token)
    try:
        online_test.register_in_contest(api)
    except ContestAPIError as e:
        if e.code == RegisterStatus.BAD_TOKEN:
            notify_admin_bad_token(campaign.pk)
        logger.error(f"Yandex.Contest api request error [id = {applicant_id}]")
        raise
    EmailQueueService.new_registration(applicant)


# FIXME: надо отлавливать все timeout'ы при запросе, т.к. в этом случае поле processed_at не будет обновлено и будет попадать в очередь задач на исполнение
# TODO: What if rq.timeouts.JobTimeoutException?
@job('default')
def import_campaign_contest_results(*, task_id):
    Campaign = apps.get_model('admission', 'Campaign')
    Task = apps.get_model('tasks', 'Task')
    try:
        task = Task.objects.unlocked(timezone.now()).get(pk=task_id)
    except Task.DoesNotExist:
        logger.error(f"Task with id = {task_id} not found.")
        return
    task.lock(locked_by="rqworker")

    filters = [Q(current=True)]
    _, task_kwargs = task.params()
    if "campaign_id" in task_kwargs:
        filters.append(Q(pk=task_kwargs["campaign_id"]))
    active_campaigns = Campaign.objects.filter(*filters)
    for campaign in active_campaigns:
        logger.info(f"Campaign id = {campaign.pk}")
        api = YandexContestAPI(access_token=campaign.access_token)

        if task_kwargs['contest_type'] not in Contest.TYPES.values:
            raise ContestAPIError

        contest_type = (Contest.TYPE_TEST
                        if task_kwargs['contest_type'] == Contest.TYPE_TEST 
                        else Contest.TYPE_EXAM)

        for contest in campaign.contests.filter(type=contest_type):
            logger.info(f"Starting processing contest {contest.pk}")
            try:
                # TODO: refactor this code without if
                if task_kwargs['contest_type'] == Contest.TYPE_TEST:
                    on_scoreboard, updated = Test.import_results(api, contest)
                else:
                    on_scoreboard, updated = Exam.import_results(api, contest)
            except ContestAPIError as e:
                if e.code == ResponseStatus.BAD_TOKEN:
                    notify_admin_bad_token(campaign.pk)
                    # FIXME: skip campaign processing instead of raising exc
                raise
            logger.info(f"Scoreboard total = {on_scoreboard}")
            logger.info(f"Updated = {updated}")
        # FIXME: если контест закончился - для всех, кого нет в scoreboard надо проставить соответствующий статус анкете и тесту.
    task.complete()
