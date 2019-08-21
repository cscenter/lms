import datetime

import pytest
import pytz

from core.urls import reverse
from courses.tests.factories import CourseTeacherFactory, AssignmentFactory
from learning.settings import StudentStatuses, Branches
from users.tests.factories import TeacherFactory, StudentFactory


@pytest.mark.django_db
def test_course_is_correspondence(settings, client):
    """Test how `tz_override` works with different user roles"""
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(2017, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course__branch__code=Branches.SPB,
                                   course__is_correspondence=False)
    teacher_nsk = TeacherFactory(branch__code=Branches.NSK)
    student_spb = StudentFactory(branch__code=Branches.SPB)
    student_nsk = StudentFactory(branch__code=Branches.NSK)
    course = assignment.course
    # Unauthenticated user doesn't see tab
    url = course.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 302
    # Any authenticated user for offline courses see timezone of the course
    for u in [student_spb, student_nsk, teacher_nsk]:
        client.login(u)
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["tz_override"] is None
    course.is_correspondence = True
    course.save()
    client.logout()
    response = client.get(course.get_absolute_url())
    assert response.status_code == 302
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
    CourseTeacherFactory(course=course, teacher=teacher_nsk)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None


@pytest.mark.django_db
def test_student_status_expelled(client, settings):
    student = StudentFactory(status=StudentStatuses.EXPELLED)
    client.login(student)
    url = reverse('study:course_list')
    response = client.get(url)
    assert response.status_code == 403
    active_student = StudentFactory()
    client.login(active_student)
    response = client.get(url)
    assert response.status_code == 200
