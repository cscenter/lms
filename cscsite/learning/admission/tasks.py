import logging

import requests
from django.apps import apps
from django.utils import translation
from django_rq import job
from post_office import mail

from core.api.yandex_contest import CONTEST_PARTICIPANTS_URL, \
    YandexContestAPIException, YandexContestAPI

logger = logging.getLogger(__name__)


@job('high')
def register_in_yandex_contest(applicant_id, language_code):
    """Register user in Yandex.Contest, then send email with summary"""
    translation.activate(language_code)
    Applicant = apps.get_model('admission', 'Applicant')
    Contest = apps.get_model('admission', 'Contest')
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "campaign__city")
                 .first())
    if not applicant.yandex_id:
        logger.error(f"Empty yandex login for applicant id = {applicant_id}")
    if not applicant.contest_id:
        logger.error(f"Empty contest id for applicant id = {applicant_id}")
        # FIXME: Get attempt to set contest id for user. If still fail - raise an Error
    campaign = applicant.campaign
    api = YandexContestAPI(access_token=campaign.access_token,
                           refresh_token=campaign.refresh_token)
    try:
        status_code, data = api.register_in_contest(applicant.yandex_id,
                                                    applicant.contest_id)
    except YandexContestAPIException as e:
        # TODO: send message to admin if token is wrong
        logger.error("Yandex.Contest request error")
        return

    # Generate notification
    update_fields = {"status_code": status_code}
    if status_code == 201:
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
