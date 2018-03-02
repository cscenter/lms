import logging
from enum import IntEnum

import requests

logger = logging.getLogger(__name__)

API_URL = 'https://api.contest.yandex.net/api/public/v2'
CONTEST_PARTICIPANTS_URL = API_URL + '/contests/{}/participants'


class RegisterStatus(IntEnum):
    CREATED = 201  # Successfully registered for contest
    BAD_TOKEN = 401  # OAuth header is not declared or is wrong
    NO_ACCESS = 403  # You have no access to this contest
    NOT_FOUND = 404  # Contest not found
    DUPLICATED = 409  # You have already registered for this contest


class YandexContestAPIException(Exception):
    pass


class YandexContestAPI:
    BASE_URL = "https://api.vk.com/method/"

    def __init__(self, access_token, refresh_token=None):
        self.access_token = access_token
        self.refresh_token = refresh_token

        self.base_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"OAuth {self.access_token}"
        }

    def register_in_contest(self, yandex_login, contest_id):
        headers = self.base_headers
        payload = {'login': yandex_login}

        api_contest_url = CONTEST_PARTICIPANTS_URL.format(contest_id)
        response = requests.post(api_contest_url,
                                 headers=headers,
                                 params=payload,
                                 timeout=3)
        if response.status_code not in [RegisterStatus.CREATED,
                                        RegisterStatus.DUPLICATED]:
            raise YandexContestAPIException(response.status_code, response.text)
        participant_id = None
        if response.status_code == RegisterStatus.CREATED:
            participant_id = response.json()
            logger.debug("Meta data: {}".format(participant_id))
        return response.status_code, participant_id
