import datetime

import pytest
from django.utils.timezone import now

from core.urls import reverse
from courses.models import CourseTeacher
from courses.tests.factories import SemesterFactory, CourseFactory
from users.tests.factories import TeacherCenterFactory


@pytest.mark.django_db
def test_teachers_list(client):
    url = reverse("api:teachers")
    t1, t2 = TeacherCenterFactory.create_batch(2)
    term = SemesterFactory.create_current()
    next_term = SemesterFactory.create_next(term)
    course1, course2 = CourseFactory.create_batch(2, semester=term,
                                                  teachers=[t1])
    course2.semester = next_term
    course2.save()
    t1.roles = CourseTeacher.roles.lecturer
    t1.save()
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2
    assert course1.meta_course_id in response.data[0]["courses"]
    assert course2.meta_course_id in response.data[0]["courses"]
    assert response.data[0]["latest_session"] == course2.semester.index
    assert response.data[0]["city"] == t1.city_id


@pytest.mark.django_db
def test_courses(client):
    url = reverse("api:courses")
    c = CourseFactory()
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == c.meta_course_id


@pytest.mark.django_db
def test_video_list(client):
    url = reverse("api:course_video_records")
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
