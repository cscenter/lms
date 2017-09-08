import logging
import os
import posixpath
import shutil

import requests
from django.apps import apps
from django.conf import settings
from django_rq import job

from core.yandex_api import YandexDiskRestAPI

logger = logging.getLogger(__name__)


@job('default')
def download_presentation_from_yandex_disk_supervisor(project_id, retries=3):
    """Download supervisor presentation to local storage by public link"""
    from learning.projects.models import project_presentation_files
    Project = apps.get_model('projects', 'Project')
    project = Project.objects.get(pk=project_id)
    file_path = _download_presentation(
        instance=project,
        public_link=project.supervisor_presentation_url,
        file_attribute_name="supervisor_presentation",
        file_path_without_ext=project_presentation_files(project, "supervisor"),
        retries=retries
    )
    return file_path


@job('default')
def download_presentation_from_yandex_disk_students(project_id, retries=3):
    """Download participants presentation to local storage by public link"""
    from learning.projects.models import project_presentation_files
    Project = apps.get_model('projects', 'Project')
    project = Project.objects.get(pk=project_id)
    file_path = _download_presentation(
        instance=project,
        public_link=project.presentation_url,
        file_attribute_name="presentation",
        file_path_without_ext=project_presentation_files(project,
                                                         "participants"),
        retries=retries
    )
    return file_path


def _download_presentation(instance, public_link, file_attribute_name,
                           file_path_without_ext, retries):
    """
    Download file by public link and save it with predefined name.

    Notes:
        We ignore original file name, but get extension from it.
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

