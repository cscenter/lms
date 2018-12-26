import datetime

import pytest
import pytz
from django.conf import settings
from django.urls import reverse

from courses.factories import CourseTeacherFactory, AssignmentFactory, \
    SemesterFactory, CourseFactory
from users.factories import TeacherCenterFactory, StudentCenterFactory


@pytest.mark.django_db
def test_course_is_correspondence(settings, client):
    """Test how `tz_override` works with different user roles"""
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(2017, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course__city_id='spb',
                                   course__is_correspondence=False)
    teacher_nsk = TeacherCenterFactory(city_id='nsk')
    student_spb = StudentCenterFactory(city_id='spb')
    student_nsk = StudentCenterFactory(city_id='nsk')
    co = assignment.course
    # Unauthenticated user doesn't see tab
    url = co.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 302
    # Any authenticated user for offline courses see timezone of the course
    for u in [student_spb, student_nsk, teacher_nsk]:
        client.login(u)
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["tz_override"] is None
    co.is_correspondence = True
    co.save()
    client.logout()
    response = client.get(co.get_absolute_url())
    assert response.status_code == 200
    # Any authenticated user (this teacher is not actual teacher of the course)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    client.login(student_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    client.login(student_spb)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['spb']
    # Actual teacher of the course
    CourseTeacherFactory(course=co, teacher=teacher_nsk)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None
    # Teacher without city, fallback to course offering timezone
    teacher = TeacherCenterFactory()
    assert teacher.city_id is None
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None


@pytest.mark.django_db
def test_course_list(client):
    student = StudentCenterFactory(city_id=settings.DEFAULT_CITY_CODE)
    client.login(student)
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(semester=s,
                              city=settings.DEFAULT_CITY_CODE)
    co_kzn = CourseFactory.create(semester=s, city="kzn")
    response = client.get(reverse('course_list_student'))
    assert len(response.context['ongoing_rest']) == 1