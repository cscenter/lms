import pytest
from django.core.files.base import ContentFile

from courses.constants import ClassTypes, MaterialVisibilityTypes
from courses.tests.factories import CourseFactory, CourseClassFactory, \
    CourseClassAttachmentFactory


@pytest.mark.django_db
def test_course_derivable_field_public_videos_count():
    course = CourseFactory()
    assert not course.public_videos_count
    CourseClassFactory(
        course=course,
        type=ClassTypes.LECTURE,
        video_url="https://link/to/youtube")
    course.refresh_from_db()
    assert course.public_videos_count == 1
    # Take into account only lectures
    CourseClassFactory(
        course=course,
        type=ClassTypes.SEMINAR,
        video_url="https://link/to/youtube")
    course.refresh_from_db()
    assert course.public_videos_count == 1
    CourseClassFactory(
        course=course,
        type=ClassTypes.LECTURE,
        video_url="")
    course.refresh_from_db()
    assert course.public_videos_count == 1
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.HIDDEN,
        course=course,
        type=ClassTypes.LECTURE,
        video_url="https://link/to/youtube")
    course.refresh_from_db()
    assert course.public_videos_count == 1


@pytest.mark.django_db
def test_course_derivable_field_public_slides_count():
    course = CourseFactory()
    slides_file = ContentFile("stub", name="test.txt")
    assert not course.public_slides_count
    cc = CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.VISIBLE,
        course=course,
        type=ClassTypes.LECTURE,
        slides=slides_file)
    course.refresh_from_db()
    assert course.public_slides_count == 1
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.VISIBLE,
        course=course,
        type=ClassTypes.SEMINAR,
        slides=slides_file)
    course.refresh_from_db()
    assert course.public_slides_count == 1
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.HIDDEN,
        course=course,
        type=ClassTypes.LECTURE,
        slides=slides_file)
    course.refresh_from_db()
    assert course.public_slides_count == 1
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.VISIBLE,
        course=course,
        type=ClassTypes.LECTURE)
    course.refresh_from_db()
    assert course.public_slides_count == 1
    cc.delete()
    course.refresh_from_db()
    assert course.public_slides_count == 0


@pytest.mark.django_db
def test_course_derivable_field_public_attachments_count():
    course = CourseFactory()
    cc = CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.VISIBLE,
        course=course,
        type=ClassTypes.LECTURE)
    course.refresh_from_db()
    assert course.public_attachments_count == 0
    cca = CourseClassAttachmentFactory(course_class=cc)
    course.refresh_from_db()
    assert course.public_attachments_count == 1
    cca.delete()
    course.refresh_from_db()
    assert course.public_attachments_count == 0
