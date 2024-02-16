import copy
import datetime
from io import StringIO
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
import pytz
from subdomains.utils import get_domain

from django.contrib.sites.models import Site
from django.core import mail, management

from core.models import SiteConfiguration
from core.tests.factories import BranchFactory, SiteConfigurationFactory, SiteFactory
from core.tests.settings import (
    ANOTHER_DOMAIN, ANOTHER_DOMAIN_ID, TEST_DOMAIN, TEST_DOMAIN_ID
)
from core.timezone.constants import DATE_FORMAT_RU
from core.urls import reverse
from courses.admin import AssignmentAdmin
from courses.constants import AssigneeMode, AssignmentFormat
from courses.models import Assignment, CourseTeacher
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseNewsFactory, CourseTeacherFactory
)
from learning.models import AssignmentNotification, CourseNewsNotification
from learning.services.enrollment_service import (
    EnrollmentService, is_course_failed_by_student
)
from learning.settings import Branches, GradeTypes, StudentStatuses
from learning.tests.factories import *
from notifications.management.commands.notify import (
    get_assignment_notification_context, get_course_news_notification_context
)
from users.services import get_student_profile
from users.tests.factories import *


def _prefixed_form(form_data, prefix: str):
    return {f"{prefix}-{k}": v for k, v in form_data.items()}


def _get_unread(client, url):
    return client.get(url).wsgi_request.unread_notifications_cache


@pytest.mark.django_db
def test_view_new_assignment(client):
    teacher1 = TeacherFactory()
    teacher2 = TeacherFactory()
    course = CourseFactory(teachers=[teacher1, teacher2])
    course_teacher1, course_teacher2 = CourseTeacher.objects.filter(course=course)
    student = StudentFactory()
    EnrollmentFactory(student=student, course=course, grade=GradeTypes.GOOD)
    a = AssignmentFactory.build()
    form = {
        'title': a.title,
        'submission_type': AssignmentFormat.ONLINE,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
        'weight': 1,
        'time_zone': 'Europe/Moscow',
        'deadline_at_0': a.deadline_at.strftime(DATE_FORMAT_RU),
        'deadline_at_1': '00:00',
        'assignee_mode': AssigneeMode.MANUAL
    }
    form_prefixed = _prefixed_form(form, "assignment")
    form_prefixed.update({
        f'responsible-teacher-{course_teacher1.pk}-active': True,
        f'responsible-teacher-{course_teacher2.pk}-active': True
    })
    client.login(teacher1)
    response = client.post(course.get_create_assignment_url(), form_prefixed)
    assert response.status_code == 302
    assignments = course.assignment_set.all()
    assert len(assignments) == 1
    assignment = assignments[0]
    student_assignment = (StudentAssignment.objects
                          .filter(assignment=assignment, student=student)
                          .get())
    assert AssignmentNotification.objects.filter(is_about_creation=True).count() == 1
    student_url = student_assignment.get_student_url()
    student_create_comment_url = reverse("study:assignment_comment_create",
                                         kwargs={"pk": student_assignment.pk})
    student_create_solution_url = reverse("study:assignment_solution_create",
                                          kwargs={"pk": student_assignment.pk})
    teacher_create_comment_url = reverse(
        "teaching:assignment_comment_create",
        kwargs={"pk": student_assignment.pk})
    teacher_url = student_assignment.get_teacher_url()
    student_list_url = reverse('study:assignment_list', args=[])
    teacher_list_url = reverse('teaching:assignments_check_queue', args=[])
    student_comment_dict = {
        'comment-text': "Test student comment without file"
    }
    teacher_comment_dict = {
        'comment-text': "Test teacher comment without file"
    }
    # Post first comment on assignment
    AssignmentNotification.objects.all().delete()
    assert not is_course_failed_by_student(course, student)
    client.login(student)
    client.post(student_create_comment_url, student_comment_dict)
    assert 2 == (AssignmentNotification.objects
                 .filter(is_about_passed=False,
                         is_unread=True,
                         is_notified=False)
                 .count())
    assert len(_get_unread(client, student_list_url).assignments) == 0
    client.login(teacher1)
    assert len(_get_unread(client, teacher_list_url).assignments) == 1
    client.login(teacher2)
    assert len(_get_unread(client, teacher_list_url).assignments) == 1
    # Read message
    client.get(teacher_url)
    client.login(teacher1)
    assert len(_get_unread(client, teacher_list_url).assignments) == 1
    client.login(teacher2)
    assert len(_get_unread(client, teacher_list_url).assignments) == 0
    # Teacher left a comment
    client.post(teacher_create_comment_url, teacher_comment_dict)
    unread_msgs_for_student = (AssignmentNotification.objects
                               .filter(user=student,
                                       is_unread=True,
                                       is_notified=False)
                               .count())
    assert unread_msgs_for_student == 1
    client.login(student)
    assert len(_get_unread(client, student_list_url).assignments) == 1
    # Student left a comment again
    client.post(student_create_comment_url, student_comment_dict)
    unread_msgs_for_teacher1 = (AssignmentNotification.objects
                                .filter(is_about_passed=False,
                                        user=teacher1,
                                        is_unread=True,
                                        is_notified=False)
                                .count())
    assert unread_msgs_for_teacher1 == 2
    # Student sent a solution
    client.login(student)
    solution_form = {
        'solution-text': "Test student solution without file"
    }
    client.post(student_create_solution_url, solution_form)
    assert 2 == (AssignmentNotification.objects
                 .filter(is_about_passed=True,
                         is_unread=True,
                         is_notified=False)
                 .count())


@pytest.mark.django_db
def test_assignment_setup_assignees_public_form(client):
    """
    Make sure `Assignment.assignees` are populated by the course
    homework reviewers on adding new assignment.
    """
    student = StudentFactory()
    t1, t2, t3, t4 = TeacherFactory.create_batch(4)
    course = CourseFactory.create(teachers=[t1, t2, t3, t4])
    course_teachers = list(CourseTeacher.objects.filter(course=course))
    for course_teacher in course_teachers:
        course_teacher.roles = CourseTeacher.roles.reviewer
        course_teacher.save()
    course_teacher1 = CourseTeacher.objects.get(course=course, teacher=t1)
    course_teacher1.notify_by_default = False
    course_teacher1.roles = None
    course_teacher1.save()
    course_teacher2 = CourseTeacher.objects.get(course=course, teacher=t2)
    EnrollmentFactory.create(student=student, course=course, grade=GradeTypes.GOOD)
    # Create first assignment
    client.login(t1)
    a = AssignmentFactory.build()
    form = {
        'title': a.title,
        'submission_type': AssignmentFormat.ONLINE,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
        'weight': '1.00',
        'time_zone': 'Europe/Moscow',
        'deadline_at_0': a.deadline_at.strftime(DATE_FORMAT_RU),
        'deadline_at_1': '00:00',
        'assignee_mode': AssigneeMode.MANUAL,
    }
    form_prefixed = _prefixed_form(form, "assignment")
    form_prefixed.update({
        f'responsible-teacher-{course_teacher1.pk}-active': True,
        f'responsible-teacher-{course_teacher2.pk}-active': True,
    })
    url = course.get_create_assignment_url()
    response = client.post(url, form_prefixed, follow=True)
    assert response.status_code == 200
    assignments = course.assignment_set.all()
    assert len(assignments) == 1
    assignment = assignments[0]
    assert len(assignment.assignees.all()) == 2
    # Update assignment and check, that assignees are not changed
    form_prefixed['maximum_score'] = 10
    url = assignment.get_update_url()
    response = client.post(url, form_prefixed)
    assert response.status_code == 302
    assigned_teachers = list(assignment.assignees.all())
    assert len(assigned_teachers) == 2
    assert course_teacher1 in assigned_teachers
    assert course_teacher2 in assigned_teachers


@pytest.mark.django_db
def test_assignment_submission_notifications_for_teacher(client):
    course = CourseFactory()
    course_teacher1, *rest_course_teachers = CourseTeacherFactory.create_batch(4,
        course=course, roles=CourseTeacher.roles.reviewer)
    course_teacher1.notify_by_default = False
    course_teacher1.save()
    # Leave a comment from student
    student = StudentFactory()
    assert not is_course_failed_by_student(course, student)
    client.login(student)
    assert Assignment.objects.count() == 0
    assignment = AssignmentFactory(course=course,
                                   assignee_mode=AssigneeMode.MANUAL,
                                   assignees=rest_course_teachers)
    student_assignment = StudentAssignmentFactory(student=student, assignment=assignment)
    student_create_comment_url = reverse("study:assignment_comment_create",
                                         kwargs={"pk": student_assignment.pk})
    client.post(student_create_comment_url,
                {'comment-text': 'test first comment'})
    notifications = [n.user.pk for n in AssignmentNotification.objects.all()]
    assert len(notifications) == 3
    assert course_teacher1.teacher_id not in notifications


@pytest.mark.django_db
def test_new_assignment_generate_notifications(settings):
    """Generate notifications for students about new assignment"""
    course = CourseFactory()
    enrollments = EnrollmentFactory.create_batch(5, course=course)
    assignment = AssignmentFactory(course=course)
    assert AssignmentNotification.objects.count() == 5
    # Dont' send notification to the students who left the course
    AssignmentNotification.objects.all().delete()
    assert AssignmentNotification.objects.count() == 0
    enrollment = enrollments[0]
    enrollment.is_deleted = True
    enrollment.save()
    assignment = AssignmentFactory(course=course)
    assert AssignmentNotification.objects.count() == 4
    # Don't create new assignment for expelled students
    AssignmentNotification.objects.all().delete()
    student = enrollments[1].student
    student_profile = get_student_profile(student, settings.SITE_ID)
    student_profile.status = StudentStatuses.EXPELLED
    student_profile.save()
    assignment = AssignmentFactory(course=course)
    assert AssignmentNotification.objects.count() == 3


@pytest.mark.parametrize("site_domain,lms_subdomain",
                         [('example.com', 'my'),
                          ('lk.example.com', None)])
@pytest.mark.django_db
def test_new_assignment_notification_context(site_domain, lms_subdomain, rf, settings):
    request = rf.request()
    request.path = '/'
    abs_url = request.build_absolute_uri
    site = SiteFactory(domain=site_domain)
    lms_domain = site_domain if not lms_subdomain else f"{lms_subdomain}.{site_domain}"
    site_settings = SiteConfigurationFactory(site=site, lms_domain=lms_domain)
    settings.SITE_ID = site.pk
    # Test configuration should correctly resolve lms urls after
    # changing settings.LMS_SUBDOMAIN
    subdomain_urlconfs = copy.deepcopy(settings.SUBDOMAIN_URLCONFS)
    lms_urlconf = subdomain_urlconfs[settings.LMS_SUBDOMAIN]
    subdomain_urlconfs[lms_subdomain] = lms_urlconf
    settings.LMS_SUBDOMAIN = lms_subdomain
    settings.SUBDOMAIN_URLCONFS = subdomain_urlconfs
    settings.DEFAULT_URL_SCHEME = 'https'
    branch_spb = BranchFactory(site=site, code="spb")
    course = CourseFactory(main_branch=branch_spb)
    enrollment = EnrollmentFactory(course=course)
    student = enrollment.student
    assignment = AssignmentFactory(course=course)
    assert AssignmentNotification.objects.count() == 1
    an = AssignmentNotification.objects.first()
    participant_branch = enrollment.student_profile.branch
    context = get_assignment_notification_context(an, participant_branch)
    student_url = abs_url(an.student_assignment.get_student_url())
    parsed_url = urlparse(student_url)
    relative_student_url = parsed_url.path
    assert context['a_s_link_student'] == student_url
    assert parsed_url.hostname == site_settings.lms_domain
    assert context['a_s_link_student'] == f"https://{parsed_url.hostname}{relative_student_url}"
    teacher_url = abs_url(an.student_assignment.get_teacher_url())
    assert context['a_s_link_teacher'] == teacher_url
    parsed_url = urlparse(teacher_url)
    assert parsed_url.hostname == site_settings.lms_domain
    assignment_link = abs_url(an.student_assignment.assignment.get_teacher_url())
    assert context['assignment_link'] == assignment_link
    assert context['course_name'] == str(course.meta_course)
    assert context['student_name'] == str(student)


@pytest.mark.django_db
def test_new_assignment_notification_context_timezone(settings, mocker):
    mocker.patch('core.locks.get_shared_connection', MagicMock())
    settings.LANGUAGE_CODE = 'ru'
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment = AssignmentFactory(course__main_branch=branch_spb,
                                   time_zone=pytz.timezone('Europe/Moscow'),
                                   deadline_at=dt)
    student = StudentFactory(branch=branch_spb)
    sa = StudentAssignmentFactory(assignment=assignment, student=student)
    dt_local = assignment.deadline_at_local()
    assert dt_local.hour == 18
    dt_str = "18:00 04 февраля"
    AssignmentNotificationFactory(is_about_creation=True, user=student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    if settings.ENABLE_NON_AUTH_NOTIFICATIONS:
        assert len(mail.outbox) == 1
        assert dt_str in mail.outbox[0].body
    else:
        assert not mail.outbox
    # If student is enrolled in the course, show assignments in the
    # timezone of the student.
    student.time_zone = branch_nsk.time_zone
    student.save()
    AssignmentNotificationFactory(is_about_creation=True, user=student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    if settings.ENABLE_NON_AUTH_NOTIFICATIONS:
        assert len(mail.outbox) == 1
        assert "22:00 04 февраля" in mail.outbox[0].body
    else:
        assert not mail.outbox


@pytest.mark.parametrize("site_domain,lms_subdomain",
                         [('example.com', 'my'),
                          ('lk.example.com', None)])
@pytest.mark.django_db
def test_new_course_news_notification_context(site_domain, lms_subdomain, settings, rf):
    site = SiteFactory(domain=site_domain)
    settings.SITE_ID = site.pk
    lms_domain = site_domain if not lms_subdomain else f"{lms_subdomain}.{site_domain}"
    site_settings = SiteConfigurationFactory(site=site, lms_domain=lms_domain)
    # Test configuration should correctly resolve lms urls after
    # changing settings.LMS_SUBDOMAIN
    subdomain_urlconfs = copy.deepcopy(settings.SUBDOMAIN_URLCONFS)
    lms_urlconf = subdomain_urlconfs[settings.LMS_SUBDOMAIN]
    subdomain_urlconfs[lms_subdomain] = lms_urlconf
    settings.LMS_SUBDOMAIN = lms_subdomain
    settings.SUBDOMAIN_URLCONFS = subdomain_urlconfs
    settings.DEFAULT_URL_SCHEME = 'https'
    request = rf.request()
    request.path = '/'
    abs_url = request.build_absolute_uri
    branch_spb = BranchFactory(site=site, code="spb")
    course = CourseFactory(main_branch=branch_spb)
    student = StudentFactory(branch=course.main_branch)
    enrollment = EnrollmentFactory(course=course, student=student)
    cn = CourseNewsNotificationFactory(course_offering_news__course=course,
                                       user=student)
    participant_branch = enrollment.student_profile.branch
    context = get_course_news_notification_context(cn, participant_branch)
    assert context['course_link'] == abs_url(course.get_absolute_url())
    site2 = SiteFactory(domain=f'another.{site_domain}')
    site2_settings = SiteConfigurationFactory(site=site2, lms_domain='test.com')
    branch_nsk = BranchFactory(code="nsk", site=site2)
    cn = CourseNewsNotificationFactory(
        course_offering_news__course=course,
        user=StudentFactory(branch=branch_nsk))
    context = get_course_news_notification_context(cn, branch_nsk)
    assert context['course_link'].startswith(f'https://{site2_settings.lms_domain}')


@pytest.mark.django_db
def test_change_assignment_comment(settings):
    """Don't send notification on editing assignment comment"""
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    enrollment = EnrollmentFactory(course=course)
    student = enrollment.student
    student_profile = enrollment.student_profile
    assignment = AssignmentFactory(course=course)
    student_assignment = StudentAssignment.objects.get(student=student,
                                                       assignment=assignment)
    assert AssignmentNotification.objects.count() == 1
    comment = AssignmentCommentFactory(student_assignment=student_assignment,
                                       author=teacher)
    assert AssignmentNotification.objects.count() == 2
    comment.text = 'New Content'
    comment.save()
    assert AssignmentNotification.objects.count() == 2
    # Get comment from db
    comment = AssignmentComment.objects.get(pk=comment.pk)
    comment.text = 'Updated Comment'
    comment.save()
    assert AssignmentNotification.objects.count() == 2


@pytest.mark.django_db
def test_changed_assignment_deadline_generate_notifications(settings):
    co = CourseFactory()
    e1, e2 = EnrollmentFactory.create_batch(2, course=co)
    s1 = e1.student
    s1_profile = get_student_profile(e1.student, settings.SITE_ID)
    s1_profile.status = StudentStatuses.EXPELLED
    s1_profile.save()
    a = AssignmentFactory(course=co)
    assert AssignmentNotification.objects.count() == 1
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    a.deadline_at = dt
    a.save()
    assert AssignmentNotification.objects.count() == 2


@pytest.mark.django_db
def test_changed_assignment_deadline_notifications_timezone(settings, mocker):
    mocker.patch('core.locks.get_shared_connection', MagicMock())
    settings.LANGUAGE_CODE = 'ru'
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    student = StudentFactory(branch=branch_nsk)
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment = AssignmentFactory(course__main_branch=branch_spb,
                                   time_zone=pytz.timezone('Asia/Novosibirsk'),
                                   deadline_at=dt)
    sa = StudentAssignmentFactory(assignment=assignment, student=student)
    dt_local = assignment.deadline_at_local()
    assert dt_local.hour == 22
    # Shows deadline in the time zone of the student
    AssignmentNotificationFactory(is_about_deadline=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    if settings.ENABLE_NON_AUTH_NOTIFICATIONS:
        assert len(mail.outbox) == 1
        assert "22:00 04 февраля" in mail.outbox[0].body
    else:
        assert not mail.outbox
    # Change student time zone
    student.time_zone = branch_spb.time_zone
    student.save()
    AssignmentNotificationFactory(is_about_deadline=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    if settings.ENABLE_NON_AUTH_NOTIFICATIONS:
        assert len(mail.outbox) == 1
        assert "18:00 04 февраля" in mail.outbox[0].body
    else:
        assert not mail.outbox


@pytest.mark.django_db
def test_remove_assignment_notifications_on_leaving_course(settings):
    course = CourseFactory()
    other_course = CourseFactory()
    enrollment = EnrollmentFactory(course=course)
    AssignmentFactory(course=course)
    an = AssignmentNotificationFactory(student_assignment__assignment__course=other_course)
    assert AssignmentNotification.objects.count() == 2
    EnrollmentService.leave(enrollment)
    assert AssignmentNotification.objects.count() == 1
    assert AssignmentNotification.objects.get() == an


@pytest.mark.django_db
def test_remove_course_news_notifications_on_leaving_course(settings):
    course = CourseFactory()
    other_course = CourseFactory()
    enrollment = EnrollmentFactory(course=course)
    CourseNewsFactory(course=course)
    cn = CourseNewsNotificationFactory(course_offering_news__course=other_course)
    assert CourseNewsNotification.objects.count() == 2
    EnrollmentService.leave(enrollment)
    assert CourseNewsNotification.objects.count() == 1
    assert CourseNewsNotification.objects.get() == cn
