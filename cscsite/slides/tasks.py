import posixpath

from django.apps import apps

from slides import yandex_disk, slideshare


def maybe_upload_slides_yandex(class_pk):
    CourseClass = apps.get_model('learning', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    # TODO: remove all jobs related to this action first? Or do it before add new job?
    course_offering = instance.course_offering
    course = course_offering.course
    yandex_disk.upload_slides(
        instance.slides.file,
        posixpath.join(course.slug, instance.slides_file_name))


def maybe_upload_slides_slideshare(class_pk):
    CourseClass = apps.get_model('learning', 'CourseClass')
    instance = CourseClass.objects.get(pk=class_pk)
    course_offering = instance.course_offering
    course = course_offering.course

    instance.slides_url = slideshare.upload_slides(
        instance.slides.file,
        "{0}: {1}".format(course_offering, instance),
        instance.description, tags=[course.slug])
    if instance.slides_url:
        CourseClass.objects.filter(pk=instance.pk).update(
            slides_url=instance.slides_url)
        return instance.slides_url