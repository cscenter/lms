import logging

from django.apps import apps
from django.utils import translation
from django_rq import job
from post_office import mail

from core.api.yandex_contest import YandexContestAPIException, YandexContestAPI, \
    RegisterStatus

logger = logging.getLogger(__name__)


@job('high')
def register_in_yandex_contest(applicant_id, language_code):
    """Register user in Yandex.Contest, then send email with summary"""
    translation.activate(language_code)
    Applicant = apps.get_model('admission', 'Applicant')
    Test = apps.get_model('admission', 'Test')
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "online_test", "campaign__city")
                 .first())
    campaign = applicant.campaign
    if not applicant.yandex_id:
        logger.error(f"Empty yandex login for applicant id = {applicant_id}")
        raise AttributeError("Empty yandex id")
    contest_id = applicant.online_test.yandex_contest_id
    if not contest_id:  # Can't imagine use case when it's possible
        logger.error(f"No contest assigned to applicant id = {applicant_id}")
        raise AttributeError("Empty contest id")
    api = YandexContestAPI(access_token=campaign.access_token,
                           refresh_token=campaign.refresh_token)
    try:
        status_code, data = api.register_in_contest(applicant.yandex_id,
                                                    contest_id)
    except YandexContestAPIException as e:
        error_status_code, text = e.args
        if error_status_code == RegisterStatus.BAD_TOKEN:
            # TODO: send message to admin if token is wrong
            pass
        logger.error(f"Yandex.Contest api request error [id = {applicant_id}]")
        raise

    # Update testing status and generate notification
    update_fields = {
        "status": Test.REGISTERED,
        "contest_status_code": status_code,
    }
    if status_code == RegisterStatus.CREATED:
        participant_id = data
        update_fields["contest_participant_id"] = participant_id
    else:  # 409 - already registered for this contest
        registered = (Test.objects
                      .filter(
                        yandex_contest_id=contest_id,
                        contest_status_code=RegisterStatus.CREATED,
                        applicant__campaign__current=True,
                        applicant__yandex_id=applicant.yandex_id)
                      .only("contest_participant_id")
                      .first())
        # Admins/judges could be registered directly through contest admin, so
        # we haven't info about there participant id and can't easily get there
        # results later, but still allow them testing application form
        if registered:
            participant_id = registered.contest_participant_id
            update_fields["contest_participant_id"] = participant_id
    (Test.objects
     .filter(applicant_id=applicant_id)
     .update(**update_fields))

    mail.send(
        [applicant.email],
        sender='CS центр <info@compscicenter.ru>',
        template=campaign.template_name,
        context={
            'FIRST_NAME': applicant.first_name,
            'SURNAME': applicant.surname,
            'PATRONYMIC': applicant.patronymic,
            'EMAIL': applicant.email,
            'CITY': applicant.campaign.city.name,
            'PHONE': applicant.phone,
            'CONTEST_ID': contest_id,
            'YANDEX_LOGIN': applicant.yandex_id,
        },
        render_on_delivery=True,
        backend='ses',
    )


@job('default')
def import_testing_results(task_id):
    Applicant = apps.get_model('admission', 'Applicant')
    Campaign = apps.get_model('admission', 'Campaign')
    current_campaigns = list(Campaign.objects
                             .filter(current=True)
                             .values_list("pk", flat=True))

    applicants = (Applicant.objects
                  .filter(status__isnull=True,
                          campagin_id__in=current_campaigns)
                  .exclude(contest_id__isnull=True))
    for applicant in applicants:
        pass
        # TODO: Если статус - duplicated, то нужно искать сначала participant_id, т.к. без него ничего не сделать.