import posixpath

from django.apps import apps
from django_rq import job

from slides import yandex_disk


@job('default')
def maybe_upload_slides_yandex(class_pk):
    CourseClass = apps.get_model('courses', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    course = instance.course
    academic_year = course.semester.get_academic_year()
    yandex_disk.upload_slides(
        instance.slides.file,
        posixpath.join(course.meta_course.slug, instance.slides_file_name),
        academic_year)
