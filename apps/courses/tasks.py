import posixpath

from django_rq import job

from django.apps import apps

from .slides import upload_slides


@job('default')
def maybe_upload_slides_yandex(class_pk):
    """Uploads local file to the yandex disk"""
    CourseClass = apps.get_model('courses', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    course = instance.course
    upload_slides(
        instance.slides.file,
        posixpath.join(course.meta_course.slug, instance.slides_file_name),
        course.semester.academic_year)
