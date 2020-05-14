import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from core.urls import reverse
from courses.tests.factories import SemesterFactory, CourseFactory, \
    AssignmentFactory
from learning.models import StudentAssignment
from learning.permissions import ViewOwnStudentAssignment
from learning.tests.factories import EnrollmentFactory, StudentAssignmentFactory
from users.tests.factories import TeacherFactory, StudentFactory


# TODO: test ViewOwnAssignment in test_permissions.py


@pytest.mark.django_db
def test_student_assignment_detail_view_permissions(client, lms_resolver,
                                                    assert_login_redirect):
    from auth.permissions import perm_registry
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher])
    student_assignment = StudentAssignmentFactory(student=student,
                                                  assignment__course=course)
    url = student_assignment.get_student_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewOwnStudentAssignment.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(url, method='get')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_student_assignment_detail_view_handle_no_permission(client):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory(teachers=[teacher])
    student_assignment = StudentAssignmentFactory(assignment__course=course)
    url = student_assignment.get_student_url()
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == student_assignment.get_teacher_url()


@pytest.mark.django_db
def test_assignment_contents(client):
    student = StudentFactory()
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student.branch, semester=semester)
    EnrollmentFactory(student=student, course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .filter(assignment=assignment, student=student)
                          .get())
    url = student_assignment.get_student_url()
    client.login(student)
    response = client.get(url)
    assert smart_bytes(assignment.text) in response.content


@pytest.mark.django_db
def test_student_assignment_detail_view_comment(client):
    student = StudentFactory()
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student.branch, semester=semester)
    EnrollmentFactory(student=student, course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment, student=student))
    student_url = student_assignment.get_student_url()
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": student_assignment.pk})
    form_data = {
        'text': "Test comment without file"
    }
    client.login(student)
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['text']) in response.content
    f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    form_data = {
        'text': "Test comment with file",
        'attached_file': f
    }
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['text']) in response.content
    assert smart_bytes('attachment1') in response.content
