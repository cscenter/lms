import logging
import requests

logger = logging.getLogger(__name__)


def request_new_access_token(*, refresh_token, client_id,
                             client_secret) -> requests.Response:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    return requests.post("https://oauth.yandex.ru/token", data=payload)


class YandexDiskException(Exception):
    pass


class YandexDiskRestAPI:
    BASE_URL = "https://cloud-api.yandex.net/v1"
    PUBLIC_RESOURCE_URL = BASE_URL + "/disk/public/resources"
    DOWNLOAD_DATA_URL = PUBLIC_RESOURCE_URL + "/download"

    def __init__(self, access_token, client_id, client_secret, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret

        self.base_headers = {
            "Accept": "application/json",
            "Host": "cloud-api.yandex.net",
        }

    def get_metadata(self, key_or_path):
        """Returns meta data for file or folder"""
        payload = {'public_key': key_or_path}
        headers = self._headers
        r = requests.get(self.PUBLIC_RESOURCE_URL,
                         headers=headers,
                         params=payload)
        self._check_status(r)
        data = r.json()
        logger.debug("Meta data in JSON: {}".format(data))
        return data

    def get_download_data(self, key_or_path):
        """Pass public_key or public url"""
        payload = {'public_key': key_or_path}
        r = requests.get(self.DOWNLOAD_DATA_URL,
                         headers=self.base_headers,
                         params=payload)
        self._check_status(r)
        data = r.json()
        logger.debug("Download data in JSON: {}".format(data))
        return data

    # FIXME: this method will change at least refresh token and doesn't make sense until settings live in process memory. Especially considering that yandex refresh token lifetime is the same as access token :<
    def update_token(self):
        r = request_new_access_token(refresh_token=self.refresh_token,
                                     client_id=self.client_id,
                                     client_secret=self.client_secret)
        self._check_status(r)
        # FIXME: check for errors: https://yandex.ru/dev/oauth/doc/dg/reference/refresh-client-docpage/
        data = r.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']

    @property
    def _headers(self):
        return {**self.base_headers,
                "Authorization": "OAuth " + self.access_token}

    @staticmethod
    def _check_status(response):
        if response.status_code != 200:
            raise YandexDiskException(response.status_code, response.text)
