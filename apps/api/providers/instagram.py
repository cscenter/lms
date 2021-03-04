import logging
import requests


logger = logging.getLogger(__name__)


class InstagramAPIException(Exception):
    pass


class InstagramAPI:
    BASE_URL = "https://graph.instagram.com"

    def __init__(self, access_token):
        self.token = access_token

        self.base_headers = {
            "Accept": "application/json",
        }

    def get_recent_posts(self, fields=None):
        """
        Get the most recent media published by the owner of the access_token.
        """
        fields = fields or ['id', 'caption', 'media_type', 'media_url', 'permalink', 'thumbnail_url', 'timestamp']
        params = {
            'access_token': self.token,
        }
        if fields:
            params['fields'] = ",".join(fields)
        response = requests.get(f'{self.BASE_URL}/me/media',
                                headers=self.base_headers,
                                params=params)
        self._check_status(response)
        data = response.json()
        return data

    def refresh_access_token(self):
        params = {
            'access_token': self.token,
            'grant_type': 'ig_refresh_token'
        }
        response = requests.get(f'{self.BASE_URL}/refresh_access_token',
                                headers=self.base_headers,
                                params=params)
        self._check_status(response)
        data = response.json()
        self.token = data['access_token']
        return data

    @staticmethod
    def _check_status(response):
        if response.status_code != 200:
            raise InstagramAPIException(response.status_code, response.text)
