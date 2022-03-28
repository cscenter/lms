import posixpath

import webdav3.client as wc
from django_rq import job

from django.apps import apps
from django.conf import settings

from .slides import upload_file


@job('default')
def maybe_upload_slides_yandex(class_pk):
    """Uploads local file to the yandex disk"""
    CourseClass = apps.get_model('courses', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    course = instance.course
    academic_year = course.semester.academic_year
    remote_path = posixpath.join(
        settings.YANDEX_DISK_SLIDES_ROOT,
        f"{academic_year}-{academic_year + 1}",
        posixpath.join(course.meta_course.slug, instance.slides_file_name))

    options = {
        'webdav_hostname': "https://webdav.yandex.ru",
        'webdav_login': settings.YANDEX_DISK_USERNAME,
        'webdav_password': settings.YANDEX_DISK_PASSWORD
    }
    client = wc.Client(options)
    upload_file(webdav_client=client, local_path=instance.slides.file.name,
                remote_path=remote_path)
