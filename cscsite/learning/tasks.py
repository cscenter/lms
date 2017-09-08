import posixpath

from django.apps import apps

from slides import yandex_disk


def maybe_upload_slides_yandex(class_pk):
    CourseClass = apps.get_model('learning', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    course_offering = instance.course_offering
    course = course_offering.course
    academic_year = course_offering.semester.get_academic_year()
    yandex_disk.upload_slides(
        instance.slides.file,
        posixpath.join(course.slug, instance.slides_file_name),
        academic_year)
