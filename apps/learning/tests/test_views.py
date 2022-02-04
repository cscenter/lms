import datetime
import logging

import pytest
from bs4 import BeautifulSoup
from testfixtures import LogCapture

from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from auth.permissions import perm_registry
from core.timezone import now_local
from core.urls import reverse
from courses.models import CourseTeacher
from courses.tests.factories import *
from learning.permissions import ViewEnrollment
from learning.tests.factories import *
from users.tests.factories import (
    CuratorFactory, StudentFactory, TeacherFactory, UserFactory
)


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
def test_course_list_view_add_news_btn_visibility(client):
    """Add news button should be hidden for users without
    CreateCourseNews permission"""
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)

    def has_add_news_btn(user):
        url = reverse('teaching:course_list')
        client.login(user)
        html = client.get(url).content.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        return soup.find('a', {
            "href": course.get_create_news_url()
        }) is not None

    assert has_add_news_btn(teacher)
    assert not has_add_news_btn(spectator)


@pytest.mark.django_db
def test_course_detail_view_basic_get(client, assert_login_redirect):
    course = CourseFactory()
    assert_login_redirect(course.get_absolute_url())
    client.login(UserFactory())
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    url = reverse('courses:course_detail', kwargs={
        "course_id": course.pk,
        "course_slug": "space-odyssey",
        "main_branch_id": course.main_branch_id,
        "semester_year": 2010,
        "semester_type": "autumn",
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
    client.login(student)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    EnrollmentFactory(student=student, course=co_other)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    EnrollmentFactory(student=student, course=co)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is not None
    assert not ctx['is_actual_teacher']
    client.logout()
    client.login(teacher)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    CourseTeacherFactory(course=co_other, teacher=teacher)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    CourseTeacherFactory(course=co, teacher=teacher)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert ctx['is_actual_teacher']


@pytest.mark.django_db
def test_course_detail_view_assignment_list(client, assert_login_redirect):
    student = StudentFactory()
    teacher = TeacherFactory()
    today = now_local(student.time_zone).date()
    next_day = today + datetime.timedelta(days=1)
    course = CourseFactory(teachers=[teacher],
                           semester=SemesterFactory.create_current(),
                           completed_at=next_day)
    course_url = course.get_absolute_url()
    EnrollmentFactory(student=student, course=course)
    a = AssignmentFactory.create(course=course)
    assert_login_redirect(course_url)
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
def test_view_course_edit_description_security(client, assert_login_redirect):
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory.create(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    url = course.get_update_url()
    assert_login_redirect(url)

    client.login(teacher_other)
    response = client.get(url)
    assert response.status_code == 403
    client.logout()

    client.login(spectator)
    response = client.get(url)
    assert response.status_code == 403
    client.logout()

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


@pytest.mark.django_db
def test_view_course_student_progress_security(client, lms_resolver):
    student = StudentFactory()
    enrollment = EnrollmentFactory(student=student)
    url = reverse('teaching:student-progress', kwargs={
        "enrollment_id": enrollment.pk,
        **enrollment.course.url_kwargs
    })
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewEnrollment.name
    assert resolver.func.view_class.permission_required in perm_registry
    user = UserFactory()
    response = client.get(url)
    assert response.status_code == 302
    client.login(user)
    response = client.get(url)
    assert response.status_code == 403
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
