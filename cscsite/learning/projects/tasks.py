import logging
import os
import posixpath

import requests
import shutil

from django.apps import apps
from django.conf import settings


logger = logging.getLogger(__name__)


def download_presentation_from_yandex_disk_supervisor(project_id, retries=3):
    """Download supervisor presentation to local storage by public link"""
    from learning.projects.models import project_presentation_files
    Project = apps.get_model('projects', 'Project')
    project = Project.objects.get(pk=project_id)
    return _download_presentation(
        instance=project,
        public_link=project.supervisor_presentation_url,
        file_attribute_name="supervisor_presentation",
        file_path_without_ext=project_presentation_files(project, "supervisor"),
        retries=retries
    )


def download_presentation_from_yandex_disk_students(project_id, retries=3):
    """Download participants presentation to local storage by public link"""
    from learning.projects.models import project_presentation_files
    Project = apps.get_model('projects', 'Project')
    project = Project.objects.get(pk=project_id)
    return _download_presentation(
        instance=project,
        public_link=project.presentation_url,
        file_attribute_name="presentation",
        file_path_without_ext=project_presentation_files(project,
                                                         "participants"),
        retries=retries
    )


def _download_presentation(instance, public_link, file_attribute_name,
                           file_path_without_ext, retries):
    """
    Download file by public link and save it with predefined name.

    Notes:
        All tasks runs in fail-safe context.
    Properties:
        object : instance
            model object
        str : file_attribute_name
            Name of attribute which store path to local file with presentation
        str : file_path_without_ext
            Relative path from media root to new file without ext
        int : retries
            Attempts to download file before fail
    """
    Project = apps.get_model('projects', 'Project')
    file_attribute = getattr(instance, file_attribute_name)
    if public_link and file_attribute != '':
        logger.warning("File path not empty for project {}. Field: {}. "
                       "Skip".format(instance.pk, file_attribute_name))
        return
    yandex_api_client = YandexDiskRestAPI()
    # Get file extension and attach it
    meta_data = yandex_api_client.get_metadata(public_link)
    _, ext = posixpath.splitext(meta_data["name"])
    file_path = file_path_without_ext + ext

    download_data = yandex_api_client.get_download_data(public_link)
    r = requests.get(download_data["href"], stream=True)
    exc = None
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    # Create all intermediate directories if not exists
    os.makedirs(posixpath.dirname(full_path),
                settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS, exist_ok=True)
    for i in range(retries):
        try:
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f, length=3 * 1024)
            instance.__class__.objects.filter(pk=instance.pk).update(
                **{file_attribute_name: file_path})
        except ValueError as e:
            exc = e
        else:
            logger.debug("File successfully saved to {}".format(full_path))
            return file_path
    logger.error("Errors occurred during file downloading for "
                 "project {}".format(instance.pk))
    raise exc


class YandexDiskException(Exception):
    pass


# TODO: Move to separated module
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
        return headers.update(self._auth_header)

    @staticmethod
    def _check_status(response):
        if response.status_code != 200:
            raise YandexDiskException(response.status_code, response.text)
