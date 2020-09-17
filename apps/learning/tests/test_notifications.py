# -*- coding: utf-8 -*-
import datetime
from io import StringIO
from urllib.parse import urlparse

import pytest
import pytz
from django.contrib.sites.models import Site
from django.core import mail, management
from subdomains.utils import get_domain

from core.models import SiteConfiguration
from core.tests.factories import BranchFactory
from core.timezone.constants import DATE_FORMAT_RU
from core.urls import reverse
from courses.admin import AssignmentAdmin
from courses.models import CourseTeacher, Assignment, \
    AssignmentSubmissionFormats
from courses.tests.factories import CourseFactory, AssignmentFactory
from learning.models import AssignmentNotification
from learning.services import course_failed_by_student, get_student_profile
from learning.settings import StudentStatuses, GradeTypes, Branches
from learning.tests.factories import *
from notifications.management.commands.notify import \
    get_assignment_notification_context, get_course_news_notification_context
from users.tests.factories import *


def _get_unread(client, url):
    return client.get(url).context['request'].unread_notifications_cache


@pytest.mark.django_db
def test_assignment(client):
    teacher1 = TeacherFactory()
    teacher2 = TeacherFactory()
    course = CourseFactory(teachers=[teacher1, teacher2])
    student = StudentFactory()
    EnrollmentFactory(student=student, course=course, grade=GradeTypes.GOOD)
    a = AssignmentFactory.build()
    form = {
        'title': a.title,
        'submission_type': AssignmentSubmissionFormats.ONLINE,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
        'weight': 1,
        'deadline_at_0': a.deadline_at.strftime(DATE_FORMAT_RU),
        'deadline_at_1': '00:00'
    }
    client.login(teacher1)
    response = client.post(course.get_create_assignment_url(), form, follow=True)
    assert response.status_code == 200
    assignments = course.assignment_set.all()
    assert len(assignments) == 1
    a = assignments[0]
    a_s = (StudentAssignment.objects
           .filter(assignment=a, student=student)
           .get())
    assert AssignmentNotification.objects.filter(is_about_creation=True).count() == 1
    student_url = a_s.get_student_url()
    student_create_comment_url = reverse("study:assignment_comment_create",
                                         kwargs={"pk": a_s.pk})
    student_create_solution_url = reverse("study:assignment_solution_create",
                                          kwargs={"pk": a_s.pk})
    teacher_create_comment_url = reverse(
        "teaching:assignment_comment_create",
        kwargs={"pk": a_s.pk})
    teacher_url = a_s.get_teacher_url()
    student_list_url = reverse('study:assignment_list', args=[])
    teacher_list_url = reverse('teaching:assignment_list', args=[])
    student_comment_dict = {
        'comment-text': "Test student comment without file"
    }
    teacher_comment_dict = {
        'comment-text': "Test teacher comment without file"
    }

    # Post first comment on assignment
    AssignmentNotification.objects.all().delete()
    assert not course_failed_by_student(course, student)
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
def test_assignment_notify_teachers_public_form(client):
    """
    On assignment creation we have to ensure that `notify_teachers`
    m2m prepopulated by the course teachers with `notify_by_default=True`
    """
    student = StudentFactory()
    t1, t2, t3, t4 = TeacherFactory.create_batch(4)
    # Course offering with 4 teachers whom notify_by_default flag set to True
    co = CourseFactory.create(teachers=[t1, t2, t3, t4])
    co_teacher1 = CourseTeacher.objects.get(course=co, teacher=t1)
    co_teacher1.notify_by_default = False
    co_teacher1.save()
    EnrollmentFactory.create(student=student, course=co, grade=GradeTypes.GOOD)
    # Create first assignment
    client.login(t1)
    a = AssignmentFactory.build()
    form = {
        'title': a.title,
        'submission_type': AssignmentSubmissionFormats.ONLINE,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
        'weight': '1.00',
        'deadline_at_0': a.deadline_at.strftime(DATE_FORMAT_RU),
        'deadline_at_1': '00:00'
    }
    url = co.get_create_assignment_url()
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    assignments = co.assignment_set.all()
    assert len(assignments) == 1
    assignment = assignments[0]
    assert len(assignment.notify_teachers.all()) == 3
    # Update assignment and check, that notify_teachers list not changed
    form['maximum_score'] = 10
    url = assignment.get_update_url()
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    assert len(assignment.notify_teachers.all()) == 3
    # Leave a comment from student
    assert not course_failed_by_student(co, student)
    client.login(student)
    sa = StudentAssignment.objects.get(assignment=assignment, student=student)
    student_create_comment_url = reverse("study:assignment_comment_create",
                                         kwargs={"pk": sa.pk})
    client.post(student_create_comment_url,
                {'comment-text': 'test first comment'})
    notifications = [n.user.pk for n in AssignmentNotification.objects.all()]
    # 1 - about assignment creation and 3 for teachers
    assert len(notifications) == 4
    assert t1.pk not in notifications
    AssignmentNotification.objects.all().delete()
    not_notify_teacher = assignment.notify_teachers.all()[0]
    assignment.notify_teachers.remove(not_notify_teacher)
    form_data = {
        'comment-text': 'second comment from student'
    }
    client.post(student_create_comment_url, form_data)
    notifications = [n.user.pk for n in AssignmentNotification.objects.all()]
    assert len(notifications) == 2
    assert not_notify_teacher not in notifications


@pytest.mark.django_db
def test_assignment_notify_teachers_admin_form(client):
    """
    On assignment creation `notify_teachers` should be prepopulated with
    the course teachers by default.
    For create view `notify_teachers` is hidden and not processed.
    """
    admin = CuratorFactory()
    client.login(admin)
    from django.contrib.admin.sites import AdminSite
    t1, t2, t3, t4 = TeacherFactory.create_batch(4)
    co = CourseFactory.create(teachers=[t1, t2, t3, t4])
    ma = AssignmentAdmin(Assignment, AdminSite())
    a = AssignmentFactory.build()
    # Send data with empty notify_teachers list
    post_data = {
        'course': co.pk,
        'title': a.title,
        'submission_type': AssignmentSubmissionFormats.ONLINE,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
        'weight': 1,
        'deadline_at_0': str(a.deadline_at.date()),
        'deadline_at_1': '00:00'
    }
    response = client.post(reverse('admin:courses_assignment_add'), post_data)
    assert (Assignment.objects.count() == 1)
    assert len(Assignment.objects.order_by('id').all()[0].notify_teachers.all()) == 4
    # Specifying teacher list on creation doesn't affect notification settings
    co_t1, co_t2, co_t3, co_t4 = CourseTeacher.objects.filter(course=co).all()
    post_data['notify_teachers'] = [co_t1.pk, co_t2.pk]
    response = client.post(reverse('admin:courses_assignment_add'), post_data)
    assert (Assignment.objects.count() == 2)
    assert len(Assignment.objects.order_by('id').all()[0].notify_teachers.all()) == 4
    assert len(Assignment.objects.order_by('id').all()[1].notify_teachers.all()) == 4


@pytest.mark.django_db
def test_new_assignment_create_notification(settings):
    course = CourseFactory()
    enrollments = EnrollmentFactory.create_batch(5, course=course)
    assignment = AssignmentFactory(course=course)
    assert AssignmentNotification.objects.count() == 5
    # Dont' send notification to the students who leaved the course
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


@pytest.mark.django_db
def test_new_assignment_create_notification_context(client, settings):
    settings.SITE_ID = 1
    settings.DEFAULT_URL_SCHEME = 'https'
    abs_url = client.get('', secure=True).wsgi_request.build_absolute_uri
    current_domain = get_domain()
    assert current_domain == settings.TEST_DOMAIN
    if settings.LMS_SUBDOMAIN:
        current_domain = f"{settings.LMS_SUBDOMAIN}.{current_domain}"
    branch_spb = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch_spb)
    enrollment = EnrollmentFactory(course=course, student__branch=branch_spb)
    student = enrollment.student
    assignment = AssignmentFactory(course=course)
    assert AssignmentNotification.objects.count() == 1
    an = AssignmentNotification.objects.first()
    site_settings = SiteConfiguration.objects.get(site_id=settings.SITE_ID)
    participant_branch = enrollment.student_profile.branch
    context = get_assignment_notification_context(an, participant_branch,
                                                  site_settings)
    student_url = abs_url(an.student_assignment.get_student_url())
    parsed_url = urlparse(student_url)
    relative_student_url = parsed_url.path
    assert context['a_s_link_student'] == student_url
    assert parsed_url.hostname == current_domain
    assert context['a_s_link_student'] == f"https://{parsed_url.hostname}{relative_student_url}"
    teacher_url = abs_url(an.student_assignment.get_teacher_url())
    assert context['a_s_link_teacher'] == teacher_url
    parsed_url = urlparse(teacher_url)
    assert parsed_url.hostname == current_domain
    assignment_link = abs_url(an.student_assignment.assignment.get_teacher_url())
    assert context['assignment_link'] == assignment_link
    assert context['course_name'] == str(course.meta_course)
    assert context['student_name'] == str(student)


@pytest.mark.django_db
def test_new_course_news_notification_context(settings, client):
    settings.SITE_ID = settings.TEST_DOMAIN_ID
    settings.DEFAULT_URL_SCHEME = 'https'
    abs_url = client.get('', secure=True).wsgi_request.build_absolute_uri
    assert get_domain() == settings.TEST_DOMAIN
    course = CourseFactory()
    student = StudentFactory(branch=course.main_branch)
    enrollment = EnrollmentFactory(course=course, student=student)
    cn = CourseNewsNotificationFactory(course_offering_news__course=course,
                                       user=student)
    context = get_course_news_notification_context(cn)
    assert context['course_link'] == abs_url(course.get_absolute_url())
    another_site = Site.objects.get(pk=settings.ANOTHER_DOMAIN_ID)
    branch = BranchFactory(code=settings.DEFAULT_BRANCH_CODE, site=another_site)
    cn = CourseNewsNotificationFactory(
        course_offering_news__course=course,
        user=StudentFactory(branch=branch))
    context = get_course_news_notification_context(cn)
    assert context['course_link'].startswith(f'https://{settings.ANOTHER_DOMAIN}')


@pytest.mark.django_db
def test_new_assignment_timezone(settings):
    settings.LANGUAGE_CODE = 'ru'
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment = AssignmentFactory(course__main_branch=branch_spb, deadline_at=dt)
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
    assert len(mail.outbox) == 1
    assert dt_str in mail.outbox[0].body
    # If student is enrolled in the course, show assignments in the
    # timezone of the student.
    student.time_zone = branch_nsk.time_zone
    student.save()
    AssignmentNotificationFactory(is_about_creation=True, user=student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert "22:00 04 февраля" in mail.outbox[0].body


@pytest.mark.django_db
def test_create_deadline_change_notification(settings):
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
def test_deadline_changed_timezone(settings):
    settings.LANGUAGE_CODE = 'ru'
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    student = StudentFactory(branch=branch_spb)
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment = AssignmentFactory(course__main_branch=branch_spb, deadline_at=dt)
    sa = StudentAssignmentFactory(assignment=assignment, student=student)
    dt_local = assignment.deadline_at_local()
    assert dt_local.hour == 18
    dt_str = "18:00 04 февраля"
    AssignmentNotificationFactory(is_about_deadline=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert dt_str in mail.outbox[0].body
    # If student is enrolled in the course, show assignments in the
    # timezone of the student.
    student.time_zone = branch_nsk.time_zone
    student.save()
    sa.assignment.course.main_branch = branch_nsk
    sa.assignment.course.save()
    AssignmentNotificationFactory(is_about_deadline=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert "22:00 04 февраля" in mail.outbox[0].body
