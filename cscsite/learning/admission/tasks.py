import logging

import requests
from django.apps import apps
from django.utils import translation
from django_rq import job
from post_office import mail

from core.api.yandex_contest import CONTEST_PARTICIPANTS_URL, \
    YandexContestAPIException
from core.settings.base import CENTER_SITE_ID

logger = logging.getLogger(__name__)


@job('high')
def application_form_send_email(applicant_id, language_code):
    """Send email with summary after application form processed"""
    Site = apps.get_model('sites', 'Site')
    site = Site.objects.get(pk=CENTER_SITE_ID)
    translation.activate(language_code)
    Applicant = apps.get_model('admission', 'Applicant')
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "campaign__city")
                 .first())
    if applicant:
        mail.send(
            [applicant.email],
            sender='info@compscicenter.ru',
            template="admission-application-form-complete",
            context={
                'FIRST_NAME': applicant.first_name,
                'SURNAME': applicant.surname,
                'PATRONYMIC': applicant.patronymic,
                'EMAIL': applicant.email,
                'CITY': applicant.campaign.city.name,
                'PHONE': applicant.phone,
                'YANDEX_LOGIN': applicant.yandex_id,
            },
            backend='ses',
        )
    else:
        logger.error("Applicant with id={} not found".format(applicant_id))


@job('high')
def register_in_yandex_contest(applicant_id):
    """
    https://api.contest.yandex.net/api/public/swagger-ui.html
    """
    AdmissionTestApplicant = apps.get_model('admission_test',
                                            'AdmissionTestApplicant')
    instance = AdmissionTestApplicant.objects.get(pk=applicant_id)

    # TODO: send message to admin if token is wrong
    # TODO: Store token in campaign settings?
    AUTH_TOKEN = 'AQAAAAAAhPQ9AATQFodbry3QokzotMSy05M4Wec'
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"OAuth {AUTH_TOKEN}"
    }
    payload = {'login': instance.yandex_id}
    contest_id = 7501
    response = requests.post(CONTEST_PARTICIPANTS_URL.format(contest_id),
                             headers=headers,
                             params=payload,
                             timeout=3)
    if response.status_code not in [201, 409]:
        raise YandexContestAPIException()

    # Generate notification
    update_fields = {"status_code": response.status_code}
    if response.status_code == 201:
        participant_id = response.text
        update_fields["participant_id"] = participant_id
        data = response.json()
        logger.debug("Meta data in JSON: {}".format(data))
    else:  # 409 - already registered for this contest
        pass
    # Saved response code from Yandex API means we processed the form
    (AdmissionTestApplicant.objects
     .filter(pk=instance.pk)
     .update(**update_fields))
    mail.send(
        [instance.email],
        sender='CS центр <info@compscicenter.ru>',
        # TODO: move template name to Campaign settings
        template="admission-2018-subscribe",
        context={
            'CONTEST_ID': contest_id,
            'YANDEX_LOGIN': instance.yandex_id,
        },
        render_on_delivery=True,
        backend='ses',
    )