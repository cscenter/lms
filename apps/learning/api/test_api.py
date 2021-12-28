from decimal import Decimal

import pytest

from core.urls import reverse
from courses.models import CourseTeacher
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.api.serializers import (
    BaseStudentAssignmentSerializer, CourseAssignmentSerializer, MyCourseSerializer
)
from learning.models import StudentAssignment
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_api_course_list_empty(settings, client):
    url = reverse("learning-api:v1:my_courses", subdomain=settings.LMS_SUBDOMAIN)
    response = client.get(url)
    assert response.status_code == 401
    teacher = TeacherFactory()
    auth_token = client.get_api_token(teacher)
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_api_course_list_with_data(settings, client):
    url = reverse("learning-api:v1:my_courses", subdomain=settings.LMS_SUBDOMAIN)
    teacher = TeacherFactory()
    other_teacher = TeacherFactory()
    course1 = CourseFactory(teachers=[teacher])
    course2 = CourseFactory(teachers=[other_teacher])
    auth_token = client.get_api_token(teacher)
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0] == MyCourseSerializer(course1).data


@pytest.mark.django_db
def test_api_course_assignments_empty(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    other_course = CourseFactory()
    url = reverse("learning-api:v1:course_assignments",
                  kwargs={'course_id': course.pk})
    AssignmentFactory(course=other_course)
    response = client.get(url)
    # Empty credentials are coerced 401 -> 403
    assert response.status_code == 403
    auth_token = client.get_api_token(teacher)
    url = reverse("learning-api:v1:course_assignments",
                  kwargs={'course_id': other_course.pk})
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 403
    url = reverse("learning-api:v1:course_assignments",
                  kwargs={'course_id': course.pk})
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_api_course_assignments_with_data(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    auth_token = client.get_api_token(teacher)
    assignment = AssignmentFactory(course=course)
    url = reverse("learning-api:v1:course_assignments",
                  kwargs={'course_id': course.pk})
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0] == CourseAssignmentSerializer(assignment).data


@pytest.mark.django_db
def test_api_course_enrollments_empty(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    other_course = CourseFactory()
    EnrollmentFactory(course=other_course)
    # Anonymous user
    url = reverse("learning-api:v1:course_enrollments",
                  kwargs={'course_id': course.pk})
    AssignmentFactory(course=other_course)
    response = client.get(url)
    assert response.status_code == 403
    # Authenticate, but request a course that teacher not participated in
    auth_token = client.get_api_token(teacher)
    url = reverse("learning-api:v1:course_enrollments",
                  kwargs={'course_id': other_course.pk})
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 403
    url = reverse("learning-api:v1:course_enrollments",
                  kwargs={'course_id': course.pk})
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_api_course_enrollments_with_data(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    enrollment1 = EnrollmentFactory(course=course, is_deleted=False)
    enrollment2 = EnrollmentFactory(course=course, is_deleted=True)
    url = reverse("learning-api:v1:course_enrollments",
                  kwargs={'course_id': course.pk})
    auth_token = client.get_api_token(teacher)
    response = client.get(url, HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_api_update_student_assignment_score(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    assignment = AssignmentFactory(course=course, maximum_score=50)
    enrollment = EnrollmentFactory(course=course, is_deleted=False)
    student_assignment = StudentAssignment.objects.get(
        assignment=assignment, student_id=enrollment.student_id)
    assert student_assignment.score is None
    url = reverse("learning-api:v1:my_course_student_assignment_update",
                  kwargs={'course_id': course.pk, 'assignment_id': assignment.pk,
                          'student_id': enrollment.student_id})
    auth_token = client.get_api_token(teacher)
    json_data = {
        'score': 20
    }
    response = client.put(url, json_data,
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    student_assignment.refresh_from_db()
    assert student_assignment.score == 20
    assert response.data == BaseStudentAssignmentSerializer(student_assignment).data
    response = client.put(url, {'score': '100500'},
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 400
    response = client.put(url, {'score': '20.4'},
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    student_assignment.refresh_from_db()
    assert student_assignment.score == Decimal('20.4')
    # Other fields are read only
    response = client.put(url, {'score': '20.4', 'execution_time': '4:00'},
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    student_assignment.refresh_from_db()
    assert student_assignment.execution_time is None


@pytest.mark.django_db
def test_api_update_student_assignment_assignee(client):
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory()
    ct1 = CourseTeacherFactory(course=course, teacher=teacher, roles=CourseTeacher.roles.lecturer)
    ct2 = CourseTeacherFactory(course=course, teacher=spectator, roles=CourseTeacher.roles.spectator)
    assignment = AssignmentFactory(course=course)
    enrollment = EnrollmentFactory(course=course, is_deleted=False)
    student_assignment = StudentAssignment.objects.get(
        assignment=assignment, student_id=enrollment.student_id)
    assert student_assignment.assignee is None
    url = reverse("learning-api:v1:my_course_student_assignment_assignee_update",
                  kwargs={'course_id': course.pk, 'assignment_id': assignment.pk,
                          'student_id': enrollment.student_id})
    auth_token = client.get_api_token(teacher)
    json_data = {
        'assignee': ct1.pk
    }
    response = client.put(url, json_data,
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 200
    student_assignment.refresh_from_db()
    assert student_assignment.assignee == ct1
    # spectator can't be assignee
    json_data = {
        'assignee': ct2.pk
    }
    response = client.put(url, json_data,
                          content_type='application/json',
                          HTTP_AUTHORIZATION=f'Token {auth_token}')
    assert response.status_code == 400
