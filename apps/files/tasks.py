import logging
import os

import requests
from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from nbconvert import HTMLExporter

logger = logging.getLogger(__file__)


def convert_ipynb_to_html(ipynb_src_path, html_dest_path):
    """
    Converts *.ipynb to html and saves the new file in the same directory with
    `html_ext` extension.
    """
    if not os.path.exists(html_dest_path):
        try:
            html_exporter = HTMLExporter()
            nb_node, _ = html_exporter.from_filename(ipynb_src_path)
            with open(html_dest_path, 'w') as f:
                f.write(nb_node)
            return True
        except (FileNotFoundError, AttributeError):
            return False
    return True


# TODO: add job on saving assignment comment if it has attachment with .ipynb file extension
# FIXME: storage won't overwrite existing file => explicitely store exported file name in the model
def maybe_convert_ipynb_to_html(*, app_name, model_name, field_name, object_id):
    """
    This task exports *.ipynb file from S3 or local file storage into html and
    saves html document in the same path as an original file.
    """
    try:
        model_class = apps.get_model(app_name, model_name)
    except LookupError:
        logger.debug(f"Model not found")
        return
    try:
        object = model_class.objects.get(pk=object_id)
    except model_class.DoesNotExist:
        logger.debug(f"Object not found")
        return True
    file_field = getattr(object, field_name, None)
    if not file_field:
        logger.debug(f"File data not found")
        return True
    _, ext = os.path.splitext(file_field.name)
    if ext != '.ipynb':
        logger.debug(f"File extension is not .ipynb")
        return True
    html_exporter = HTMLExporter()
    if settings.USE_S3_FOR_UPLOAD:
        signed_url = file_field.url
        try:
            with requests.get(signed_url, allow_redirects=True, stream=True) as r:
                nb_node, _ = html_exporter.from_file(r.raw)
            html_dest_path = file_field.name + '.html'
        except (FileNotFoundError, AttributeError):
            logger.debug(f"nbconvert failed to import {file_field.path} from s3")
            return False
    else:
        # FIXME: What if html file already exists? (e.g. was uploaded by user)
        try:
            nb_node, _ = html_exporter.from_filename(file_field.path)
            html_dest_path = file_field.path + '.html'
        except (FileNotFoundError, AttributeError):
            return False
    file_field.storage.save(html_dest_path, ContentFile(nb_node.encode()))
    return True
