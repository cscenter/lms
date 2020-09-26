import logging
import os
import posixpath
import shutil
from datetime import timedelta

import django_rq
import requests
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.fields.files import FieldFile
from django_rq import job

from api.providers.yandex_disk import YandexDiskRestAPI

logger = logging.getLogger(__name__)


class DownloadPresentationError(Exception):
    pass


REQUIRED_SETTINGS = [
    "YANDEX_DISK_CLIENT_ID",
    "YANDEX_DISK_CLIENT_SECRET",
    "YANDEX_DISK_ACCESS_TOKEN",
    "YANDEX_DISK_REFRESH_TOKEN"
]
for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(f"Please add {attr} to your settings module")

YANDEX_DISK_API_DATA = {
    "client_id": settings.YANDEX_DISK_CLIENT_ID,
    "client_secret": settings.YANDEX_DISK_CLIENT_SECRET,
    "access_token": settings.YANDEX_DISK_ACCESS_TOKEN,
    "refresh_token": settings.YANDEX_DISK_REFRESH_TOKEN,
}


@job('default')
def download_presentation_from_yandex_disk_supervisor(project_id, retries=3):
    """Download supervisor presentation to local storage by public link"""
    Project = apps.get_model('projects', 'Project')
    project = Project.objects.get(pk=project_id)
    file_path = _download_file_from_yandex_disk(
        public_url=project.supervisor_presentation_url,
        file_field=project.supervisor_presentation,
        file_name="supervisor",
        caller=download_presentation_from_yandex_disk_supervisor,
        retries=retries)
    return file_path


@job('default')
def download_presentation_from_yandex_disk_students(project_id, retries=3):
    """Download participants presentation to local storage by public link"""
    Project = apps.get_model('projects', 'Project')
    project = Project.objects.get(pk=project_id)
    file_path = _download_file_from_yandex_disk(
        public_url=project.presentation_url,
        file_field=project.presentation,
        file_name="participants",
        caller=download_presentation_from_yandex_disk_students,
        retries=retries)
    return file_path


def _download_file_from_yandex_disk(public_url: str,
                                    file_field: FieldFile,
                                    file_name: str,
                                    caller,
                                    retries: int):
    """Download file by public url and save to the storage."""
    instance = file_field.instance
    if public_url and file_field != '':
        logger.warning("Project {} already has a file value for field {}. "
                       "Skip".format(instance.pk, file_field.field.name))
        return

    client = YandexDiskRestAPI(**YANDEX_DISK_API_DATA)

    meta_data = client.get_metadata(public_url)
    _, ext = posixpath.splitext(meta_data["name"])
    file_name = file_name + ext
    file_path = file_field.field.upload_to(instance, file_name)

    try:
        r = requests.get(meta_data["file"], stream=True,
                         # connect and read timeouts
                         timeout=(3, 20))
        actual_file_path = file_field.storage.save(file_path, r.raw)
        instance.__class__.objects.filter(pk=instance.pk).update(
            **{file_field.field.name: actual_file_path})
        return actual_file_path
    except (requests.ConnectionError, requests.Timeout) as e:
        if not retries:
            msg = (f"Failed to download {file_field.field.name} for "
                   f"project {instance.pk}")
            raise DownloadPresentationError(msg) from e
        scheduler = django_rq.get_scheduler('default')
        scheduler.enqueue_in(timedelta(minutes=1),
                             caller,
                             instance.pk,
                             retries=retries - 1)
