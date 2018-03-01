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
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "campaign__city")
                 .first())
    if not applicant.yandex_id:
        logger.error(f"Empty yandex login for applicant id = {applicant_id}")
        raise AttributeError("Empty yandex id")
    if not applicant.contest_id:
        applicant.refresh_contest_id()
        if not applicant.contest_id:
            logger.error(f"Empty contest id for applicant id = {applicant_id}")
            raise AttributeError("Empty contest id")
    campaign = applicant.campaign
    api = YandexContestAPI(access_token=campaign.access_token,
                           refresh_token=campaign.refresh_token)
    try:
        status_code, data = api.register_in_contest(applicant.yandex_id,
                                                    applicant.contest_id)
    except YandexContestAPIException as e:
        error_status_code, text = e.args
        if error_status_code == RegisterStatus.BAD_TOKEN:
            # TODO: send message to admin if token is wrong
            pass
        logger.error(f"Yandex.Contest api request error [id = {applicant_id}]")
        raise

    # Generate notification
    update_fields = {"status_code": status_code}
    if status_code == RegisterStatus.CREATED:
        participant_id = data
        update_fields["participant_id"] = participant_id
    else:  # 409 - already registered for this contest
        pass
    # Saved response code from Yandex API means we processed application form
    (Applicant.objects
     .filter(pk=applicant_id)
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
            'CONTEST_ID': applicant.contest_id,
            'YANDEX_LOGIN': applicant.yandex_id,
        },
        render_on_delivery=True,
        backend='ses',
    )
