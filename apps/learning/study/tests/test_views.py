import pytest
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from core.urls import reverse
from courses.tests.factories import SemesterFactory, CourseFactory, \
    AssignmentFactory
from learning.models import StudentAssignment, AssignmentNotification, \
    AssignmentComment
from learning.permissions import ViewOwnStudentAssignment
from learning.tests.factories import EnrollmentFactory, \
    StudentAssignmentFactory, AssignmentCommentFactory
from users.tests.factories import TeacherFactory, StudentFactory, \
    StudentProfileFactory


# TODO: test ViewOwnAssignment in test_permissions.py


@pytest.mark.django_db
def test_student_assignment_detail_view_permissions(client, lms_resolver,
                                                    assert_login_redirect):
    from auth.permissions import perm_registry
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher],
                           semester=SemesterFactory.create_current())
    AssignmentFactory(course=course)
    EnrollmentFactory(student=student, course=course)
    student_assignment = StudentAssignment.objects.get(student=student)
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
    student_profile = StudentProfileFactory()
    student = student_profile.user
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student_profile.branch, semester=semester)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
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
    student_profile = StudentProfileFactory()
    student = student_profile.user
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student_profile.branch, semester=semester)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment, student=student))
    student_url = student_assignment.get_student_url()
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": student_assignment.pk})
    form_data = {
        'comment-text': "Test comment without file"
    }
    client.login(student)
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    form_data = {
        'comment-text': "Test comment with file",
        'comment-attached_file': f
    }
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    assert smart_bytes('attachment1') in response.content


@pytest.mark.django_db
def test_new_comment_on_assignment_page(client, assert_redirect):
    semester = SemesterFactory.create_current()
    student_profile = StudentProfileFactory()
    teacher = TeacherFactory()
    teacher2 = TeacherFactory()
    course = CourseFactory(main_branch=student_profile.branch, semester=semester,
                           teachers=[teacher, teacher2])
    EnrollmentFactory(student_profile=student_profile,
                      student=student_profile.user,
                      course=course)
    a = AssignmentFactory.create(course=course)
    a_s = (StudentAssignment.objects
           .filter(assignment=a, student=student_profile.user)
           .get())
    client.login(student_profile.user)
    detail_url = a_s.get_student_url()
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": a_s.pk})
    recipients_count = 2
    assert AssignmentNotification.objects.count() == 1
    n = AssignmentNotification.objects.first()
    assert n.is_about_creation
    # Publish new comment
    AssignmentNotification.objects.all().delete()
    form_data = {
        'comment-text': "Test comment with file",
        'comment-attached_file': SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, detail_url)
    response = client.get(detail_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    assert smart_bytes('attachment1') in response.content
    assert AssignmentNotification.objects.count() == recipients_count
    # Create new draft comment
    assert AssignmentComment.objects.count() == 1
    AssignmentNotification.objects.all().delete()
    form_data = {
        'comment-text': "Test comment 2 with file",
        'comment-attached_file': SimpleUploadedFile("a.txt", b"a_content"),
        'save-draft': 'Submit button text'
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, detail_url)
    assert AssignmentComment.objects.count() == 2
    assert AssignmentNotification.objects.count() == 0
    response = client.get(detail_url)
    assert 'comment_form' in response.context_data
    form = response.context_data['comment_form']
    assert form_data['comment-text'] == form.instance.text
    rendered_form = BeautifulSoup(str(form), "html.parser")
    file_name = rendered_form.find('span', class_='fileinput-filename')
    assert file_name and file_name.string == form.instance.attached_file_name
    # Publish another comment. This one should override draft comment.
    # But first create draft comment from another teacher and make sure
    # it won't be published on publishing new comment from the first teacher
    teacher2_draft = AssignmentCommentFactory(author=teacher2,
                                              student_assignment=a_s,
                                              is_published=False)
    assert AssignmentComment.published.count() == 1
    draft = AssignmentComment.objects.get(text=form_data['comment-text'])
    form_data = {
        'comment-text': "Updated test comment 2 with file",
        'comment-attached_file': SimpleUploadedFile("test_file_b.txt", b"b_content"),
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, detail_url)
    assert AssignmentComment.published.count() == 2
    assert AssignmentNotification.objects.count() == recipients_count
    draft.refresh_from_db()
    assert draft.is_published
    assert draft.attached_file_name.startswith('test_file_b')
    teacher2_draft.refresh_from_db()
    assert not teacher2_draft.is_published