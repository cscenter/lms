import pytest

from django.core.files.base import ContentFile

from courses.constants import ClassTypes, MaterialVisibilityTypes
from courses.tests.factories import (
    CourseClassAttachmentFactory, CourseClassFactory, CourseFactory
)


@pytest.mark.django_db
def test_course_derivable_field_public_videos_count():
    course = CourseFactory(materials_visibility=MaterialVisibilityTypes.PUBLIC)
    assert not course.public_videos_count
    CourseClassFactory(
        course=course,
        type=ClassTypes.LECTURE,
        video_url="https://link/to/youtube",
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    course.refresh_from_db()
    assert course.public_videos_count == 1
    # Take into account only lectures
    CourseClassFactory(
        course=course,
        type=ClassTypes.SEMINAR,
        video_url="https://link/to/youtube",
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    course.refresh_from_db()
    assert course.public_videos_count == 2
    CourseClassFactory(
        course=course,
        type=ClassTypes.LECTURE,
        video_url="",
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    course.refresh_from_db()
    assert course.public_videos_count == 2
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.PARTICIPANTS,
        course=course,
        type=ClassTypes.LECTURE,
        video_url="https://link/to/youtube")
    course.refresh_from_db()
    assert course.public_videos_count == 2


@pytest.mark.django_db
def test_course_derivable_field_public_slides_count(mocker):
    mocker.patch("courses.tasks.maybe_upload_slides_yandex.delay")
    course = CourseFactory()
    slides_file = ContentFile("stub", name="test.txt")
    assert not course.public_slides_count
    cc = CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.PUBLIC,
        course=course,
        type=ClassTypes.LECTURE,
        slides=slides_file)
    course.refresh_from_db()
    assert course.public_slides_count == 1
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.PUBLIC,
        course=course,
        type=ClassTypes.SEMINAR,
        slides=slides_file)
    course.refresh_from_db()
    assert course.public_slides_count == 2
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.PARTICIPANTS,
        course=course,
        type=ClassTypes.LECTURE,
        slides=slides_file)
    course.refresh_from_db()
    assert course.public_slides_count == 2
    CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.PUBLIC,
        course=course,
        type=ClassTypes.LECTURE)
    course.refresh_from_db()
    assert course.public_slides_count == 2
    cc.delete()
    course.refresh_from_db()
    assert course.public_slides_count == 1


@pytest.mark.django_db
def test_course_derivable_field_public_attachments_count():
    course = CourseFactory()
    cc = CourseClassFactory(
        materials_visibility=MaterialVisibilityTypes.PUBLIC,
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
