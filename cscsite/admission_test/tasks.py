import logging

import requests
from django.apps import apps
from django_rq import job
from post_office import mail


logger = logging.getLogger(__name__)

API_URL = 'https://api.contest.yandex.net/api/public/v2'
CONTEST_PARTICIPANTS_URL = API_URL + '/contests/{}/participants'


class YandexAPIException(Exception):
    pass


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
        raise YandexAPIException()

    # Send notification
    if response.status_code == 201:
        participant_id = response.text
        (AdmissionTestApplicant.objects
         .filter(pk=instance.pk)
         .update(participant_id=participant_id))
        data = response.json()
        logger.debug("Meta data in JSON: {}".format(data))
        mail.send(
            [instance.email],
            sender='info@compscicenter.ru',
            # TODO: move template name to Campaign settings
            template="admission-2018-subscribe",
            context={
                'CONTEST_ID': contest_id,
                'YANDEX_LOGIN': instance.yandex_id,
                'PARTICIPANT_ID': participant_id,
            },
            render_on_delivery=True,
            backend='ses',
        )
    else:  # 409 - already registered for this contest
        # TODO: Send reminder?
        pass



