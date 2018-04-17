import logging
from enum import IntEnum

import requests

logger = logging.getLogger(__name__)

API_URL = 'https://api.contest.yandex.net/api/public/v2'
PARTICIPANTS_URL = API_URL + '/contests/{}/participants'
PARTICIPANT_URL = API_URL + '/contests/{contest_id}/participants/{participant_id}'
CONTEST_URL = API_URL + '/contests/{contest_id}'
STANDINGS_URL = API_URL + '/contests/{contest_id}/standings'


class RegisterStatus(IntEnum):
    CREATED = 201  # Successfully registered for contest
    BAD_TOKEN = 401  # OAuth header is not declared or is wrong
    NO_ACCESS = 403  # You have no access to this contest
    NOT_FOUND = 404  # Contest not found
    DUPLICATED = 409  # You have already registered for this contest


class ResponseStatus(IntEnum):
    SUCCESS = 200
    BAD_REQUEST = 400  # Bad Request
    BAD_TOKEN = 401  # OAuth header is not declared or is wrong
    NO_ACCESS = 403  # You don't have enough permissions
    NOT_FOUND = 404  # User or contest not found
    NOT_ALLOWED = 405  # Method Not Allowed


STANDINGS_PARAMS = {
    'page': 'page',
    'page_size': 'pageSize',
    'for_judge': 'forJudge',  # something about freezing submissions
    # Participants can start contest after ending if allowed in settings
    'show_virtual': 'showVirtual',
    # Admins can attach results from external log without having
    # participants submissions.
    'show_external': 'showExternal',
    'locale': 'locale',
    'participant': 'participantSearch',
    'participant_group_id': 'userGroupId'
}


class YandexContestAPIException(Exception):
    pass


# TODO: catch read timeout exceptions in api?
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
        api_contest_url = PARTICIPANTS_URL.format(contest_id)
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

    def contest_info(self, contest_id):
        headers = self.base_headers
        url = CONTEST_URL.format(contest_id=contest_id)
        response = requests.get(url, headers=headers, timeout=1)
        if response.status_code != ResponseStatus.SUCCESS:
            raise YandexContestAPIException(response.status_code, response.text)
        info = response.json()
        logger.debug("Meta data: {}".format(info))
        return response.status_code, info

    def participant_info(self, contest_id, participant_id):
        headers = self.base_headers
        url = PARTICIPANT_URL.format(contest_id=contest_id,
                                     participant_id=participant_id)
        response = requests.get(url, headers=headers, timeout=1)
        if response.status_code != ResponseStatus.SUCCESS:
            raise YandexContestAPIException(response.status_code, response.text)
        info = response.json()
        logger.debug("Meta data: {}".format(info))
        return response.status_code, info

    def standings(self, contest_id, **params):
        """Scoreboard for those who started contest and sent anything"""
        headers = self.base_headers
        url = STANDINGS_URL.format(contest_id=contest_id)
        if "page_size" not in params:
            params["page_size"] = 100
        if "locale" not in params:
            params["locale"] = "ru"
        # Due to the features of the `shad` monitor, set for_judge to True
        if "for_judge" not in params:
            params["for_judge"] = True
        if "show_external" not in params:
            params["show_external"] = False
        if "show_virtual" not in params:
            params["show_virtual"] = False
        for bool_attr in ["for_judge", "show_external", "show_virtual"]:
            params[bool_attr] = str(params[bool_attr]).lower()
        payload = {}
        for param_key, param_value in params.items():
            key = STANDINGS_PARAMS.get(param_key, param_key)
            payload[key] = param_value
        logger.debug(f"Payload: {payload}")
        response = requests.get(url, headers=headers, params=payload, timeout=3)
        if response.status_code != ResponseStatus.SUCCESS:
            raise YandexContestAPIException(response.status_code, response.text)
        json_data = response.json()
        logger.debug(f"Meta data: {json_data}")
        return response.status_code, json_data
