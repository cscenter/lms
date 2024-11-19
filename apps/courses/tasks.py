import logging
import posixpath

import webdav3.client as wc
from django_rq import job

from django.apps import apps
from django.conf import settings

from courses.models import Semester
from users.models import StudentProfile, StudentTypes

from .slides import upload_file

logger = logging.getLogger(__name__)

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

@job('default')
def recalculate_invited_priority(semester_id = None):
    try:
        semester = Semester.objects.get(id=semester_id)
        profiles = StudentProfile.objects.filter(type=StudentTypes.INVITED,
                                                 invitation__semester=semester)
    except Semester.DoesNotExist:
        current_semester = Semester.get_current()
        previos_semester = current_semester.get_prev()
        preprevios_semester = previos_semester.get_prev()
        logger.warning(f"Semester with ID {semester_id} is not found. Updating 3 last semesters: "
                       f"{preprevios_semester}, {previos_semester} and {current_semester}")
        profiles = StudentProfile.objects.filter(type=StudentTypes.INVITED,
                                                 invitation__semester__in=[preprevios_semester, previos_semester, current_semester])
    for profile in profiles:
        profile.save()
