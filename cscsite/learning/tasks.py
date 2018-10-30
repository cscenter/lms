import posixpath

from django.apps import apps
from django_rq import job

from slides import yandex_disk


@job('default')
def maybe_upload_slides_yandex(class_pk):
    CourseClass = apps.get_model('learning', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    course_offering = instance.course_offering
    meta_course = course_offering.meta_course
    academic_year = course_offering.semester.get_academic_year()
    yandex_disk.upload_slides(
        instance.slides.file,
        posixpath.join(meta_course.slug, instance.slides_file_name),
        academic_year)
