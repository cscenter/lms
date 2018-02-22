import logging
import requests


logger = logging.getLogger(__name__)


# May expire at any moment
# https://www.instagram.com/developer/authentication/
ACCESS_TOKEN = '4945952248.d26b5a4.bb2898accaa546f0a156cb5e65ca9945'


class InstagramAPIException(Exception):
    pass


class InstagramAPI:
    BASE_URL = "https://api.instagram.com/v1"

    def __init__(self, access_token=ACCESS_TOKEN):
        self.token = access_token

        self.base_headers = {
            "Accept": "application/json",
        }

    def get_recent_post(self, **kwargs):
        """
        Get the most recent media published by the owner of the access_token.
        """
        payload = {
            'count': 1,
            'access_token': self.token
        }
        for k, v in kwargs.items():
            payload[k] = v
        response = requests.get(f'{self.BASE_URL}/users/self/media/recent/',
                                headers=self.base_headers,
                                params=payload)
        self._check_status(response)
        data = response.json()
        logger.debug("Meta data in JSON: {}".format(data))
        return data

    @staticmethod
    def _check_status(response):
        if response.status_code != 200:
            raise InstagramAPIException(response.status_code, response.text)
