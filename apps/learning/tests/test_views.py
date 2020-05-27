# -*- coding: utf-8 -*-
import datetime
import logging

import pytest
from django.utils.encoding import smart_bytes
from testfixtures import LogCapture

from core.timezone import now_local
from core.urls import branch_aware_reverse, reverse
from courses.tests.factories import *
from learning.tests.factories import *
from users.tests.factories import StudentFactory, TeacherFactory, \
    CuratorFactory


# TODO: Написать тест, который проверяет, что по-умолчанию в форму
# редактирования описания ПРОЧТЕНИЯ подставляется описание из курса. И описание прочтения, если оно уже есть.
# TODO: test redirects on course offering page if tab exists but user has no access
# TODO: test assignment deadline


@pytest.mark.skip("Add PermissionRequiredMixin to the view")
@pytest.mark.django_db
def test_course_list_view_permissions(client, assert_login_redirect):
    url = reverse('teaching:course_list')
    assert_login_redirect(url)
    student = StudentFactory()
    client.login(student)
    assert client.get(url).status_code == 403
    client.login(TeacherFactory())
    assert client.get(url).status_code == 200
    client.login(CuratorFactory())
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_course_detail_view_basic_get(client):
    course = CourseFactory()
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    url = branch_aware_reverse('courses:course_detail', kwargs={
        "course_slug": "space-odyssey",
        "semester_year": 2010,
        "semester_type": "autumn",
        "branch_code_request": ""
    })
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_course_detail_view_course_user_relations(client):
    """
    Testing is_enrolled and is_actual_teacher here
    """
    student = StudentFactory()
    teacher = TeacherFactory()
    co = CourseFactory.create()
    co_other = CourseFactory.create()
    url = co.get_absolute_url()
    ctx = client.get(url).context
    client.login(student)
    ctx = client.get(url).context
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    EnrollmentFactory(student=student, course=co_other)
    ctx = client.get(url).context
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    EnrollmentFactory(student=student, course=co)
    ctx = client.get(url).context
    assert ctx['request_user_enrollment'] is not None
    assert not ctx['is_actual_teacher']
    client.logout()
    client.login(teacher)
    ctx = client.get(url).context
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    CourseTeacherFactory(course=co_other, teacher=teacher)
    ctx = client.get(url).context
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    CourseTeacherFactory(course=co, teacher=teacher)
    ctx = client.get(url).context
    assert ctx['request_user_enrollment'] is None
    assert ctx['is_actual_teacher']


@pytest.mark.django_db
def test_course_detail_view_assignment_list(client):
    student = StudentFactory()
    teacher = TeacherFactory()
    today = now_local(student.get_timezone()).date()
    next_day = today + datetime.timedelta(days=1)
    course = CourseFactory(teachers=[teacher],
                           semester=SemesterFactory.create_current(),
                           completed_at=next_day)
    course_url = course.get_absolute_url()
    EnrollmentFactory(student=student, course=course)
    a = AssignmentFactory.create(course=course)
    response = client.get(course_url)
    assert response.status_code == 200
    client.login(student)
    assert smart_bytes(a.title) in client.get(course_url).content
    a_s = StudentAssignment.objects.get(assignment=a, student=student)
    assert smart_bytes(a_s.get_student_url()) in client.get(course_url).content
    a_s.delete()
    with LogCapture(level=logging.INFO) as l:
        assert client.get(course_url).status_code == 200
        l.check(('learning.tabs',
                 'INFO',
                 f"no StudentAssignment for "
                 f"student ID {student.pk}, assignment ID {a.pk}"))
    client.login(teacher)
    assert smart_bytes(a.title) in client.get(course_url).content
    assert smart_bytes(a.get_teacher_url()) in client.get(course_url).content


@pytest.mark.django_db
def test_course_edit_description_security(client, assert_login_redirect):
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    url = co.get_update_url()
    assert_login_redirect(url)
    client.login(teacher_other)
    assert_login_redirect(url)
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_smoke(client):
    evt = EventFactory.create()
    url = evt.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 200
    assert evt.name.encode() in response.content
    assert smart_bytes(evt.venue.get_absolute_url()) in response.content
