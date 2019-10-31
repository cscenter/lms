import datetime

import pytest
from django.utils.timezone import now

from core.urls import reverse
from courses.models import CourseTeacher
from courses.tests.factories import SemesterFactory, CourseFactory, \
    CourseTeacherFactory
from learning.tests.factories import GraduateProfileFactory
from users.constants import Roles
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_teachers_list(client, settings):
    url = reverse("public-api:v2:teachers")
    teacher1, teacher2 = TeacherFactory.create_batch(2)
    term = SemesterFactory.create_current()
    next_term = SemesterFactory.create_next(term)
    course1 = CourseFactory(semester=term)
    course2 = CourseFactory(semester=next_term)
    t1_c1 = CourseTeacherFactory(teacher=teacher1, course=course1,
                                 roles=CourseTeacher.roles.lecturer)
    t1_c2 = CourseTeacherFactory(teacher=teacher1, course=course2,
                                 roles=CourseTeacher.roles.lecturer)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2
    assert course1.meta_course_id in response.data[0]["courses"]
    assert course2.meta_course_id in response.data[0]["courses"]
    assert response.data[0]["latest_session"] == course2.semester.index
    assert response.data[0]["branch"] == teacher1.branch.code
    # Make sure `pure reviewers` are not in the results.
    t2_c1 = CourseTeacherFactory(teacher=teacher2, course=course1,
                                 roles=CourseTeacher.roles.reviewer)
    response = client.get(url)
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2
    # Teacher could be in the results but in one of the course he
    # participated as a `reviewer only`. Avoid this course in the
    # teacher.`courses` list since it's used for filtering teachers, not just
    # displaying info where teacher has been participated
    t1_c1.roles = CourseTeacher.roles.reviewer
    t1_c1.save()
    response = client.get(url)
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 1
    assert response.data[0]["courses"] == [course2.meta_course_id]
    # If teacher has many roles in the course, it still should be in
    # the results
    t1_c1.roles = CourseTeacher.roles.reviewer | CourseTeacher.roles.lecturer
    t1_c1.save()
    response = client.get(url)
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2
    # Case when no roles were provided, hide this teacher from the list
    t1_c1.roles = 0
    t1_c1.save()
    response = client.get(url)
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 1
    # Test for duplicates if user has teacher role on different sites
    t1_c1.roles = CourseTeacher.roles.seminar
    t1_c1.save()
    response = client.get(url)
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2
    teacher1.add_group(Roles.TEACHER, site_id=settings.ANOTHER_DOMAIN_ID)
    response = client.get(url)
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2


@pytest.mark.django_db
def test_courses(client):
    url = reverse("public-api:v2:teachers_meta_courses")
    c = CourseFactory()
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == c.meta_course_id


@pytest.mark.django_db
def test_video_list(client):
    url = reverse("public-api:v2:course_videos")
    CourseFactory.create_batch(2, is_published_in_video=False)
    with_video = CourseFactory.create_batch(5,
                                            is_published_in_video=True)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 5
    assert set(x.id for x in with_video) == set(x['id'] for x in response.data)
    today = now().date()
    future_day = today + datetime.timedelta(days=3)
    course = CourseFactory(is_published_in_video=True, completed_at=future_day)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 5


@pytest.mark.django_db
def test_api_testimonials_smoke(client):
    GraduateProfileFactory(testimonial='test', photo='stub.JPG')
    response = client.get(reverse("public-api:v2:testimonials"))
    assert response.status_code == 200
    assert len(response.data['results']) == 1