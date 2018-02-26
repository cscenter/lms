import logging
import requests


logger = logging.getLogger(__name__)


CSCENTER_GROUP_ID = -25297429
CSCENTER_SERVICE_TOKEN = 'df1e9aaddf1e9aaddf1e9aadf8df7ff97addf1edf1e9aad8590329c193e4513b8deec8f'


class VkAPIException(Exception):
    pass


class VkOpenAPI:
    BASE_URL = "https://api.vk.com/method/"

    def __init__(self, access_token=None, service_token=CSCENTER_SERVICE_TOKEN):
        self.access_token = access_token
        self.service_token = service_token

        self.base_headers = {
            "Accept": "application/json",
        }

    def get_wall(self, owner_id, **kwargs):
        """
        Returns a list of posts on a user wall or community wall.
        https://vk.com/dev/wall.get
        """
        payload = {
            'v': 5.73,
            'extended': 0,
            'filter': 'owner',
            'count': 1,
            'owner_id': owner_id,
            'access_token': self.service_token
        }
        for k, v in kwargs.items():
            payload[k] = v
        response = requests.get(f'{self.BASE_URL}/wall.get',
                                headers=self.base_headers,
                                params=payload)
        self._check_status(response)
        data = response.json()
        logger.debug("Meta data in JSON: {}".format(data))
        return data

    @staticmethod
    def _check_status(response):
        if response.status_code != 200:
            raise VkAPIException(response.status_code, response.text)
