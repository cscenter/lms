import logging
import requests
# TODO: move to api/ ?

logger = logging.getLogger(__name__)


class YandexDiskException(Exception):
    pass


class YandexDiskRestAPI(object):
    BASE_URL = "https://cloud-api.yandex.net/v1"
    PUBLIC_RESOURCE_URL = BASE_URL + "/disk/public/resources"
    DOWNLOAD_DATA_URL = PUBLIC_RESOURCE_URL + "/download"

    def __init__(self, token=None):
        self.token = token

        self.base_headers = {
            "Accept": "application/json",
            "Host": "cloud-api.yandex.net"
        }
        if self.token:
            self._auth_header = {"Authorization": "OAuth " + self.token}

    def get_metadata(self, key_or_path, public=True):
        """
        Returns meta data for file or folder.

        Required token if file/folder not published
        """
        payload = {'public_key': key_or_path}
        headers = self.base_headers
        if not public:
            headers = self._attach_token_header(headers)
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

    def _attach_token_header(self, headers):
        if not hasattr(self, "_auth_header"):
            raise YandexDiskException("Set token first")
        headers.update(self._auth_header)

    @staticmethod
    def _check_status(response):
        if response.status_code != 200:
            raise YandexDiskException(response.status_code, response.text)