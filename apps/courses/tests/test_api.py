import pytest

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
    c1, c2 = CourseFactory.create_batch(2, semester=term, teachers=[t1])
    c2.semester = next_term
    c2.save()
    t1.roles = CourseTeacher.roles.lecturer
    t1.save()
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert len(response.data[0]["courses"]) == 2
    assert c1.meta_course_id in response.data[0]["courses"]
    assert c2.meta_course_id in response.data[0]["courses"]
    assert response.data[0]["last_session"] == c2.semester.index
    assert response.data[0]["city"] == t1.city_id


@pytest.mark.django_db
def test_courses(client):
    url = reverse("api:courses")
    c = CourseFactory()
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == c.meta_course_id
