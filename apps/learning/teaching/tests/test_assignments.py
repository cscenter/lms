import datetime
from decimal import Decimal

import pytest
import pytz
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import formats
from django.utils.encoding import smart_bytes

from contests.constants import CheckingSystemTypes
from core.urls import reverse
from courses.models import AssignmentSubmissionFormats, Assignment
from courses.tests.factories import AssignmentFactory, CourseFactory, \
    CourseTeacherFactory, SemesterFactory, CourseNewsFactory
from learning.models import Enrollment, StudentAssignment, \
    AssignmentNotification, CourseNewsNotification, AssignmentComment
from learning.settings import Branches
from learning.tests.factories import StudentAssignmentFactory, \
    EnrollmentFactory, AssignmentCommentFactory
from users.tests.factories import TeacherFactory, StudentFactory, \
    StudentProfileFactory


# TODO: Преподавание -> Задания, добавить тест для deadline_local


@pytest.mark.django_db
def test_assignment_public_form(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    teacher = TeacherFactory()
    course_spb = CourseFactory(teachers=[teacher])
    client.login(teacher)
    form_data = {
        "submission_type": AssignmentSubmissionFormats.ONLINE,
        "title": "title",
        "text": "text",
        "deadline_at_0": "29.06.2017",
        "deadline_at_1": "00:00",
        "passing_score": "3",
        "maximum_score": "5",
        "weight": "1.00"
    }
    add_url = course_spb.get_create_assignment_url()
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    assert Assignment.objects.count() == 1
    assignment = Assignment.objects.first()
    # DB stores datetime values in UTC
    assert assignment.deadline_at.day == 28
    assert assignment.deadline_at.hour == 21
    assert assignment.deadline_at.minute == 0
    assert assignment.course_id == course_spb.pk
    tz_diff = datetime.timedelta(hours=3)  # UTC+3 for msk timezone
    assert assignment.deadline_at_local().utcoffset() == tz_diff
    # Check widget shows local time
    response = client.get(assignment.get_update_url())
    widget_html = response.context['form']['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00'
    # Clone CO from msk
    co_in_nsk = CourseFactory(main_branch__code=Branches.NSK,
                              meta_course=course_spb.meta_course,
                              teachers=[teacher])
    add_url = co_in_nsk.get_create_assignment_url()
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    assert Assignment.objects.count() == 2
    assignment_last = Assignment.objects.order_by("pk").last()
    assert assignment_last.course_id == co_in_nsk.pk
    tz_diff = datetime.timedelta(hours=7)  # UTC+7 for nsk timezone
    assert assignment_last.deadline_at_local().utcoffset() == tz_diff
    assert assignment_last.deadline_at.hour == 17


@pytest.mark.django_db
def test_assignment_detail_deadline_l10n(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    teacher = TeacherFactory()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course__main_branch__code=Branches.SPB,
                                   course__teachers=[teacher])
    url_for_teacher = assignment.get_teacher_url()
    client.login(teacher)
    response = client.get(url_for_teacher)
    html = BeautifulSoup(response.content, "html.parser")
    # Note: On this page used `naturalday` filter, so use passed datetime
    deadline_str = formats.date_format(assignment.deadline_at_local(),
                                       'd E Y H:i')
    assert deadline_str == "01 января 2017 18:00"
    assert any(deadline_str in s.string for s in html.find_all('p'))
    # Test student submission page
    sa = StudentAssignmentFactory(assignment=assignment)
    response = client.get(sa.get_teacher_url())
    html = BeautifulSoup(response.content, "html.parser")
    # Note: On this page used `naturalday` filter, so use passed datetime
    deadline_str = formats.date_format(assignment.deadline_at_local(),
                                       'd E Y H:i')
    assert deadline_str == "01 января 2017 18:00"
    assert any(deadline_str in s.string for s in
               html.find_all('span', {"class": "nowrap"}))


@pytest.mark.django_db
def test_student_assignment_submission_grade(client):
    """
    Make sure we can remove zeroed grade for student assignment and use both
    1.23 and 1,23 formats
    """
    sa = StudentAssignmentFactory()
    teacher = TeacherFactory.create()
    CourseTeacherFactory(course=sa.assignment.course,
                         teacher=teacher)
    sa.assignment.passing_score = 1
    sa.assignment.maximum_score = 10
    sa.assignment.save()
    assert sa.score is None
    student = sa.student
    form = {"score": 0, "grading_form": True}
    client.login(teacher)
    response = client.post(sa.get_teacher_url(), form, follow=True)
    assert response.status_code == 200
    sa.refresh_from_db()
    assert sa.score == 0
    form = {"score": "", "grading_form": True}
    response = client.post(sa.get_teacher_url(), form, follow=True)
    assert response.status_code == 200
    sa.refresh_from_db()
    assert sa.score is None
    form = {"score": "1.22", "grading_form": True}
    response = client.post(sa.get_teacher_url(), form, follow=True)
    sa.refresh_from_db()
    assert sa.score == Decimal("1.22")
    form = {"score": "2,34", "grading_form": True}
    response = client.post(sa.get_teacher_url(), form, follow=True)
    sa.refresh_from_db()
    assert sa.score == Decimal("2.34")


@pytest.mark.django_db
def test_create_assignment_public_form(client):
    """Create assignments for active enrollments only"""
    ss = StudentFactory.create_batch(3)
    current_semester = SemesterFactory.create_current()
    co = CourseFactory.create(semester=current_semester)
    for student in ss:
        enrollment = EnrollmentFactory.create(student=student, course=co)
    assert Enrollment.objects.count() == 3
    assert StudentAssignment.objects.count() == 0
    assignment = AssignmentFactory.create(course=co)
    assert StudentAssignment.objects.count() == 3
    enrollment.is_deleted = True
    enrollment.save()
    assignment = AssignmentFactory.create(course=co)
    assert StudentAssignment.objects.count() == 5
    assert StudentAssignment.objects.filter(student=enrollment.student,
                                            assignment=assignment).count() == 0
    # Check deadline notifications sent for active enrollments only
    AssignmentNotification.objects.all().delete()
    assignment.deadline_at = assignment.deadline_at - datetime.timedelta(days=1)
    assignment.save()
    enrolled_students = Enrollment.active.count()
    assert enrolled_students == 2
    assert AssignmentNotification.objects.count() == enrolled_students
    CourseNewsNotification.objects.all().delete()
    assert CourseNewsNotification.objects.count() == 0
    CourseNewsFactory.create(course=co)
    assert CourseNewsNotification.objects.count() == enrolled_students


@pytest.mark.django_db
def test_student_assignment_detail_view_add_comment(client):
    teacher = TeacherFactory()
    enrollment = EnrollmentFactory(course__teachers=[teacher])
    student = enrollment.student
    a = AssignmentFactory.create(course=enrollment.course)
    a_s = (StudentAssignment.objects
           .filter(assignment=a, student=student)
           .get())
    teacher_url = a_s.get_teacher_url()
    create_comment_url = reverse("teaching:assignment_comment_create",
                                 kwargs={"pk": a_s.pk})
    form_data = {
        'comment-text': "Test comment without file"
    }
    client.login(teacher)
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == teacher_url
    response = client.get(teacher_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    form_data = {
        'comment-text': "Test comment with file",
        'comment-attached_file': SimpleUploadedFile("attachment1.txt",
                                            b"attachment1_content")
    }
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == teacher_url
    response = client.get(teacher_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    assert smart_bytes('attachment1') in response.content


@pytest.mark.django_db
def test_student_assignment_draft_comment(client, assert_redirect):
    """
    Draft comment shouldn't send any notification until publishing.
    New published comment should replace draft comment record.
    """
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
    client.login(teacher)
    teacher_detail_url = a_s.get_teacher_url()
    create_comment_url = reverse("teaching:assignment_comment_create",
                                 kwargs={"pk": a_s.pk})
    recipients_count = 1
    assert AssignmentNotification.objects.count() == 1
    n = AssignmentNotification.objects.first()
    assert n.is_about_creation
    # Publish new comment
    AssignmentNotification.objects.all().delete()
    form_data = {
        'comment-text': "Test comment with file",
        'comment-attached_file': SimpleUploadedFile("attachment1.txt",
                                                    b"attachment1_content")
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, teacher_detail_url)
    response = client.get(teacher_detail_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    assert smart_bytes('attachment1') in response.content
    assert AssignmentNotification.objects.count() == recipients_count
    # Create draft message
    assert AssignmentComment.objects.count() == 1
    AssignmentNotification.objects.all().delete()
    form_data = {
        'comment-text': "Test comment 2 with file",
        'comment-attached_file': SimpleUploadedFile("a.txt", b"a_content"),
        'save-draft': 'Submit button text'
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, teacher_detail_url)
    assert AssignmentComment.objects.count() == 2
    assert AssignmentNotification.objects.count() == 0
    response = client.get(teacher_detail_url)
    assert 'comment_form' in response.context_data
    form = response.context_data['comment_form']
    assert form_data['comment-text'] == form.instance.text
    rendered_form = BeautifulSoup(str(form), "html.parser")
    file_name = rendered_form.find('span', class_='fileinput-filename')
    assert file_name and file_name.string == form.instance.attached_file_name
    draft = AssignmentComment.objects.get(text=form_data['comment-text'])
    assert not draft.is_published
    # Publish another draft comment - this one should override the previous one
    # Make sure it won't touch draft comments from other users
    teacher2_draft = AssignmentCommentFactory(author=teacher2,
                                              student_assignment=a_s,
                                              is_published=False)
    assert AssignmentComment.published.count() == 1
    form_data = {
        'comment-text': "Updated test comment 2 with file",
        'comment-attached_file': SimpleUploadedFile("test_file_b.txt", b"b_content"),
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, teacher_detail_url)
    assert AssignmentComment.published.count() == 2
    assert AssignmentNotification.objects.count() == recipients_count
    draft.refresh_from_db()
    assert draft.is_published
    assert draft.attached_file_name.startswith('test_file_b')
    teacher2_draft.refresh_from_db()
    assert not teacher2_draft.is_published
