import datetime

import pytest
import pytz
from bs4 import BeautifulSoup

from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from core.urls import reverse
from courses.models import CourseGroupModes
from courses.permissions import ViewAssignment
from courses.tests.factories import AssignmentFactory, CourseFactory, SemesterFactory
from learning.models import StudentAssignment
from learning.permissions import ViewStudentAssignment, ViewStudentAssignmentList
from learning.settings import Branches
from learning.tests.factories import (
    AssignmentCommentFactory, CourseTeacherFactory, EnrollmentFactory,
    StudentAssignmentFactory, StudentGroupAssigneeFactory, StudentGroupFactory
)
from users.tests.factories import CuratorFactory, StudentFactory, TeacherFactory


@pytest.mark.django_db
def test_teaching_index_page_smoke(client):
    """Just to make sure this view doesn't return 50x error"""
    response = client.get(reverse("teaching:base"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_student_assignment_list_view_permissions(client, lms_resolver,
                                                  assert_login_redirect):
    from auth.permissions import perm_registry
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher])
    url = reverse('teaching:assignment_list')
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewStudentAssignmentList.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(url, method='get')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 403
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_student_assignment_list_view_redirect(client, lms_resolver,
                                               assert_login_redirect):
    """
    Teacher will be redirected if no courses where he participated were found
    """
    teacher = TeacherFactory()
    url = reverse('teaching:assignment_list')
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse('teaching:course_list')


@pytest.mark.django_db
def test_student_assignment_list_view_filters(client):
    url = reverse('teaching:assignment_list')
    # Default filter for grade - `no_grade`
    teacher = TeacherFactory()
    students = StudentFactory.create_batch(3)
    s = SemesterFactory.create_current(for_branch=Branches.SPB)
    # some other teacher's course offering
    co_other = CourseFactory.create(semester=s)
    AssignmentFactory.create_batch(2, course=co_other)
    client.login(teacher)
    # no course offerings yet, return 302
    response = client.get(url)
    assert response.status_code == 302
    # Create co, assignments and enroll students
    co = CourseFactory.create(semester=s, teachers=[teacher])
    for student1 in students:
        EnrollmentFactory.create(student=student1, course=co)
    assignment = AssignmentFactory.create(course=co)
    response = client.get(url)
    # TODO: add wrong term type and check redirect.
    # By default we show all submissions without grades
    assert len(response.context['student_assignment_list']) == 3
    # Show submissions without comments
    response = client.get(url + "?comment=empty")
    assert len(response.context['student_assignment_list']) == 3
    # TODO: add test which assignment selected by default.
    sas = {(StudentAssignment.objects.get(student=student,
                                          assignment=assignment))
           for student in students}
    assert set(sas) == set(response.context['student_assignment_list'])
    assert len(sas) == len(response.context['student_assignment_list'])
    # Let's check assignments with last comment from student only
    response = client.get(url + "?comment=student")
    assert len(response.context['student_assignment_list']) == 0
    # Teacher commented on student1 assignment
    student1, student2, student3 = students
    sa1: StudentAssignment = StudentAssignment.objects.get(
        student=student1, assignment=assignment)
    sa2 = StudentAssignment.objects.get(student=student2,
                                        assignment=assignment)
    AssignmentCommentFactory.create(student_assignment=sa1, author=teacher)
    sa1.refresh_from_db()
    assert sa1.last_comment_from == sa1.CommentAuthorTypes.TEACHER
    response = client.get(url + "?comment=any")
    assert len(response.context['student_assignment_list']) == 3
    response = client.get(url + "?comment=student")
    assert len(response.context['student_assignment_list']) == 0
    response = client.get(url + "?comment=teacher")
    assert len(response.context['student_assignment_list']) == 1
    response = client.get(url + "?comment=empty")
    assert len(response.context['student_assignment_list']) == 2
    # Student2 commented on assignment
    AssignmentCommentFactory.create_batch(2, student_assignment=sa2,
                                          author=student2)
    response = client.get(url + "?comment=any")
    assert len(response.context['student_assignment_list']) == 3
    response = client.get(url + "?comment=student")
    assert len(response.context['student_assignment_list']) == 1
    assert {sa2} == set(response.context['student_assignment_list'])
    response = client.get(url + "?comment=teacher")
    assert len(response.context['student_assignment_list']) == 1
    response = client.get(url + "?comment=empty")
    assert len(response.context['student_assignment_list']) == 1
    # Teacher answered on the student2 assignment
    AssignmentCommentFactory.create(student_assignment=sa2, author=teacher)
    response = client.get(url + "?comment=any")
    assert len(response.context['student_assignment_list']) == 3
    response = client.get(url + "?comment=student")
    assert len(response.context['student_assignment_list']) == 0
    response = client.get(url + "?comment=teacher")
    assert len(response.context['student_assignment_list']) == 2
    response = client.get(url + "?comment=empty")
    assert len(response.context['student_assignment_list']) == 1
    # Student 3 add comment on assignment
    sa3 = StudentAssignment.objects.get(student=student3,
                                        assignment=assignment)
    AssignmentCommentFactory.create_batch(3, student_assignment=sa3,
                                          author=student3)
    response = client.get(url + "?comment=any")
    assert len(response.context['student_assignment_list']) == 3
    response = client.get(url + "?comment=student")
    assert len(response.context['student_assignment_list']) == 1
    response = client.get(url + "?comment=teacher")
    assert len(response.context['student_assignment_list']) == 2
    response = client.get(url + "?comment=empty")
    assert len(response.context['student_assignment_list']) == 0
    # teacher has set a grade
    sa3.score = 3
    sa3.save(update_fields=['score'])
    response = client.get(url + "?comment=student&score=no")
    assert len(response.context['student_assignment_list']) == 0
    response = client.get(url + "?comment=student&score=any")
    assert len(response.context['student_assignment_list']) == 1
    sa3.refresh_from_db()
    sa1.score = 3
    sa1.save(update_fields=['score'])
    response = client.get(url + "?comment=student&score=yes")
    assert len(response.context['student_assignment_list']) == 1


# TODO: test ViewOwnAssignment in courses/tests/test_permissions.py


@pytest.mark.django_db
def test_assignment_detail_view_permissions(client, lms_resolver,
                                            assert_login_redirect):
    from auth.permissions import perm_registry
    teacher = TeacherFactory()
    student = StudentFactory()
    assignment = AssignmentFactory(course__teachers=[teacher])
    url = assignment.get_teacher_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewAssignment.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(url, method='get')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 403
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200
    client.login(CuratorFactory())
    response = client.get(url)
    assert response.status_code == 200


# TODO: test ViewStudentAssignment in test_permissions.py

@pytest.mark.django_db
def test_student_assignment_detail_view_permissions(client, lms_resolver,
                                                    assert_login_redirect):
    from auth.permissions import perm_registry
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher])
    student_assignment = StudentAssignmentFactory(student=student,
                                                  assignment__course=course)
    url = student_assignment.get_teacher_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewStudentAssignment.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(url, method='get')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 403
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_assignment_detail_view_details(client):
    teacher = TeacherFactory()
    student = StudentFactory()
    s = SemesterFactory.create_current(for_branch=Branches.SPB)
    co = CourseFactory.create(semester=s, teachers=[teacher])
    a = AssignmentFactory.create(course=co)
    client.login(teacher)
    url = a.get_teacher_url()
    response = client.get(url)
    assert response.context['assignment'] == a
    assert len(response.context['a_s_list']) == 0
    EnrollmentFactory.create(student=student, course=co)
    a_s = StudentAssignment.objects.get(student=student, assignment=a)
    response = client.get(url)
    assert response.context['assignment'] == a
    assert {a_s} == set(response.context['a_s_list'])
    assert len(response.context['a_s_list']) == 1


@pytest.mark.django_db
def test_assignment_contents(client):
    teacher = TeacherFactory()
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course=co)
    a = AssignmentFactory.create(course=co)
    a_s = (StudentAssignment.objects
           .get(assignment=a, student=student))
    client.login(teacher)
    assert smart_bytes(a.text) in client.get(a_s.get_teacher_url()).content


@pytest.mark.django_db
def test_student_assignment_detail_view_grading_form(client):
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    student = StudentFactory()
    EnrollmentFactory.create(student=student, course=co)
    a = AssignmentFactory.create(course=co, maximum_score=13)
    a_s = (StudentAssignment.objects
           .get(assignment=a, student=student))
    url = a_s.get_teacher_url()
    grade_form = {
        'grading_form': True,
        'score': 11
    }
    client.login(teacher)
    response = client.post(url, grade_form)
    assert response.status_code == 302
    assert response.url == url
    assert StudentAssignment.objects.get(pk=a_s.pk).score == 11
    response = client.get(url)
    assert b"value=\"11\"" in response.content
    assert smart_bytes("/{}".format(13)) in response.content
    # wrong grading value can't be set
    grade_form['score'] = 42
    client.post(url, grade_form)
    assert client.post(url, grade_form).status_code == 400
    assert StudentAssignment.objects.get(pk=a_s.pk).score == 11


@pytest.mark.django_db
def test_student_assignment_detail_view_context_next_unchecked(client):
    teacher = TeacherFactory()
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    co_other = CourseFactory.create()
    EnrollmentFactory.create(student=student, course=co)
    EnrollmentFactory.create(student=student, course=co_other)
    a1, a2 = AssignmentFactory.create_batch(2, course=co)
    a_other = AssignmentFactory.create(course=co_other)
    a_s1 = (StudentAssignment.objects
            .get(assignment=a1, student=student))
    a_s2 = (StudentAssignment.objects
            .get(assignment=a2, student=student))
    a_s_other = (StudentAssignment.objects
                 .get(assignment=a_other, student=student))
    url1 = a_s1.get_teacher_url()
    url2 = a_s2.get_teacher_url()
    client.login(teacher)
    assert client.get(url1).context['next_student_assignment'] is None
    assert client.get(url2).context['next_student_assignment'] is None
    [AssignmentCommentFactory.create(author=a_s.student,
                                     student_assignment=a_s)
     for a_s in [a_s1, a_s2]]
    assert client.get(url1).context['next_student_assignment'] == a_s2
    assert client.get(url2).context['next_student_assignment'] == a_s1


@pytest.mark.django_db
def test_gradebook_list(client, mocker, assert_redirect):
    # This test will fail if current term is of a summer type since we
    # omit summer semesters in the gradebook list view
    mocked = mocker.patch('courses.utils.now_local')
    msk_tz = pytz.timezone("Europe/Moscow")
    mocked.return_value = msk_tz.localize(datetime.datetime(2021, 5, 1, 12, 0))
    teacher = TeacherFactory()
    client.login(teacher)
    gradebooks_url = reverse("teaching:gradebook_list")
    response = client.get(gradebooks_url)
    assert response.status_code == 200
    # Redirect if there is only one course in the current term
    semester = SemesterFactory.create_current()
    course = CourseFactory(semester=semester, teachers=[teacher])
    response = client.get(gradebooks_url)
    assert_redirect(response, course.get_gradebook_url())
    course2 = CourseFactory(semester=semester, teachers=[teacher])
    response = client.get(gradebooks_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_student_group_manual_link(client):

    """
    Checking correct displaying link on student group in teacher course list
    """

    def soup_request():
        course_list = reverse("teaching:course_list")
        response = client.get(course_list)
        soup = BeautifulSoup(response.content, "html.parser")
        return soup

    teacher = TeacherFactory()

    # check without student group link
    course_branch_group = CourseFactory.create(teachers=[teacher])
    StudentGroupFactory.create(course=course_branch_group)
    client.login(teacher)
    soup = soup_request()
    assert soup.find(class_='test_student_manual_group') is None

    # check with student group link
    course_manual_group = CourseFactory.create(teachers=[teacher],
                                               group_mode=CourseGroupModes.MANUAL)
    StudentGroupFactory.create(course=course_manual_group)
    soup = soup_request()
    assert soup.find(class_='test_student_manual_group') is not None


@pytest.mark.django_db
def test_student_groups_list(client):

    """
    Checking correct displaying student groups in teacher group list
    """

    teacher = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher],
                                  group_mode=CourseGroupModes.MANUAL)
    student_group = StudentGroupFactory.create(course=course)
    student_group_1 = StudentGroupFactory.create(course=course)

    client.login(teacher)
    student_group_list = course.get_student_groups_url()
    response = client.get(student_group_list)
    soup = BeautifulSoup(response.content, "html.parser")

    assert soup.find(text=student_group.name) is not None
    assert soup.find(text=student_group_1.name) is not None


@pytest.mark.django_db
def test_student_groups_detail(client):

    """
    Checking correct displaying student and assignees in group
    """

    teacher = TeacherFactory()
    curator = CuratorFactory()
    student = StudentFactory()
    student1 = StudentFactory()
    s = SemesterFactory.create_current(for_branch=Branches.SPB)
    course = CourseFactory.create(semester=s, teachers=[teacher], group_mode=CourseGroupModes.MANUAL)
    sg1 = StudentGroupFactory.create(course=course)
    sg2 = StudentGroupFactory.create()
    EnrollmentFactory.create(student=student, course=course, student_group=sg1)
    course_teacher = CourseTeacherFactory()
    StudentGroupAssigneeFactory(assignee=course_teacher, student_group=sg1)

    client.login(teacher)
    student_group_list = sg1.student_group_detail()

    response = client.get(student_group_list)
    soup = BeautifulSoup(response.content, "html.parser")
    assert sg1.name in soup.find('h2').text
    assert student.last_name in soup.find(id="student_list").text
    assert student1.last_name not in soup.find(id="student_list").text
    assert course_teacher.teacher.last_name in soup.find(id="teacher_list").text
