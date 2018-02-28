import logging

import requests

logger = logging.getLogger(__name__)

API_URL = 'https://api.contest.yandex.net/api/public/v2'
CONTEST_PARTICIPANTS_URL = API_URL + '/contests/{}/participants'


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
        if response.status_code not in [201, 409]:
            raise YandexContestAPIException(response.status_code, response.text)
        data = response.json()
        logger.debug("Meta data in JSON: {}".format(data))
        return response.status_code, data
