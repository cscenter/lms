import logging

from django.apps import apps
from django.utils import translation, timezone
from django_rq import job

from admission.models import Test, Contest
from admission.services import EmailQueueService
from api.providers.yandex_contest import YandexContestAPI, RegisterStatus, \
    ContestAPIError

logger = logging.getLogger(__name__)


def notify_admin_bad_token(campaign_id):
    """Send message about bad auth token for Yandex.Contest API"""
    pass


# FIXME: Add tests, c'mon
@job('high')
def register_in_yandex_contest(applicant_id, language_code):
    """Register user in Yandex.Contest, then send email with summary"""
    translation.activate(language_code)
    Applicant = apps.get_model('admission', 'Applicant')
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "campaign__branch", "online_test")
                 .first())
    if not applicant.yandex_id:
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
def import_testing_results(task_id=None):
    Campaign = apps.get_model('admission', 'Campaign')
    Task = apps.get_model('tasks', 'Task')
    if task_id:
        try:
            task = Task.objects.unlocked(timezone.now()).get(pk=task_id)
        except Task.DoesNotExist:
            logger.error(f"Task with id = {task_id} doesn't exist.")
            return
    task.lock(locked_by="rqworker")
    current_campaigns = Campaign.objects.filter(current=True)
    if not current_campaigns:
        # TODO: mark task as failed
        return
    now = timezone.now()
    # Campaigns are the same now, but handle them separately,
    # since this behavior can be changed in the future.
    for campaign in current_campaigns:
        api = YandexContestAPI(access_token=campaign.access_token)
        for contest in campaign.contests.filter(type=Contest.TYPE_TEST).all():
            contest_id = contest.contest_id
            logger.debug(f"Starting processing contest {contest_id}")

            try:
                on_scoreboard, updated = Test.import_results(api, contest)
            except ContestAPIError as e:
                if e.code == RegisterStatus.BAD_TOKEN:
                    notify_admin_bad_token(campaign.pk)
                logger.error(f"Yandex.Contest API error. "
                             f"Method: `standings` "
                             f"Contest: {contest_id}")
                raise
            logger.debug(f"Total participants {on_scoreboard}")
            logger.debug(f"Updated {updated}")
        # FIXME: если контест закончился - для всех, кого нет в scoreboard надо проставить соответствующий статус анкете и тесту.
    task.processed_at = timezone.now()
    task.save()
