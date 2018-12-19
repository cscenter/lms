# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from courses.models import Course, CourseClassAttachment


class Command(BaseCommand):
    help = "Recalculate `Course` derivable fields starting with `materials_*`"

    def handle(self, *args, **options):
        for co in Course.objects.only('pk', 'materials_slides',
                                      'materials_video',
                                      'materials_files').all():
            has_class_slides = False
            has_class_materials_files = False
            has_class_video = False
            for course_class in co.courseclass_set.only('slides',
                                                        'video_url',
                                                        'course_id').all():
                if course_class.slides:
                    has_class_slides = True
                if course_class.video_url.strip() != "":
                    has_class_video = True
            if (CourseClassAttachment.objects
                    .filter(course_class__course_id=co.pk).exists()):
                has_class_materials_files = True
            if (co.materials_slides != has_class_slides or
                    co.materials_video != has_class_video or
                    co.materials_files != has_class_materials_files):
                Course.objects.filter(pk=co.pk).update(
                    materials_slides=has_class_slides,
                    materials_video=has_class_video,
                    materials_files=has_class_materials_files
                )
