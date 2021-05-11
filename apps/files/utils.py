import os
from typing import Optional

import requests
from nbconvert import HTMLExporter

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile

from files.tasks import logger


class ConvertError(Exception):
    pass


def convert_ipynb_to_html(file_field: FieldFile,
                          name=None) -> Optional[ContentFile]:
    """
    Returns in-memory html version of the .ipynb file stored in S3 or locally.
    """
    if not file_field:
        logger.debug(f"File field or data not found")
        return
    _, ext = os.path.splitext(file_field.name)
    if ext != '.ipynb':
        logger.debug(f"File extension is not .ipynb")
        return
    html_exporter = HTMLExporter()
    if settings.USE_CLOUD_STORAGE:
        signed_url = file_field.url
        try:
            with requests.get(signed_url, allow_redirects=True, stream=True) as r:
                nb_node, _ = html_exporter.from_file(r.raw)
        except (FileNotFoundError, AttributeError) as e:
            logger.debug(f"nbconvert failed to import {file_field.path} from s3")
            raise ConvertError from e
    else:
        try:
            nb_node, _ = html_exporter.from_filename(file_field.path)
        except (FileNotFoundError, AttributeError) as e:
            raise ConvertError from e
    name = name or file_field.name + '.html'
    return ContentFile(nb_node.encode(), name=name)
    # file_field.storage.save(new_path, ContentFile(nb_node.encode()))
