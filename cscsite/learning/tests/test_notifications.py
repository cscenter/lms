# -*- coding: utf-8 -*-

from io import StringIO

import pytest
import pytz
from django.core import mail, management
from django.test import TestCase

from learning.admin import AssignmentAdmin
from learning.settings import DATE_FORMAT_RU, StudentStatuses, GradeTypes
from users.factories import TeacherCenterFactory
from .mixins import *
from ..factories import *


class NotificationTests(MyUtilitiesMixin, TestCase):
    def _get_unread(self, url):
        return (self.client.get(url)
                .context['request']
                .unread_notifications_cache)

    def test_assignment(self):
        student = StudentCenterFactory()
        teacher1 = TeacherCenterFactory()
        teacher2 = TeacherCenterFactory()
        co = CourseFactory(teachers=[teacher1, teacher2])
        EnrollmentFactory(student=student, course=co, grade=GradeTypes.good)
        # Notify_teachers m2m populated only from view action
        self.doLogin(teacher1)
        a = AssignmentFactory.build()
        form = {'title': a.title,
                'is_online': 1,
                'text': a.text,
                'passing_score': 0,
                'maximum_score': 5,
                'deadline_at_0': a.deadline_at.strftime(DATE_FORMAT_RU),
                'deadline_at_1': '00:00'
        }
        url = co.get_create_assignment_url()
        response = self.client.post(url, form, follow=True)
        assert response.status_code == 200
        assignments = co.assignment_set.all()
        assert len(assignments) == 1
        a = assignments[0]
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        student_url = a_s.get_student_url()
        teacher_url = a_s.get_teacher_url()
        student_list_url = reverse('assignment_list_student', args=[])
        teacher_list_url = reverse('assignment_list_teacher', args=[])
        student_comment_dict = {'text': "Test student comment without file"}
        teacher_comment_dict = {'text': "Test teacher comment without file"}

        # Post first comment on assignment
        assert not co.failed_by_student(student)
        self.doLogin(student)
        self.client.post(student_url, student_comment_dict)
        # FIXME(Dmitry): this should not affect this test, fix&remove
        self.client.get(student_url)
        self.assertEquals(2, (AssignmentNotification.objects
                              .filter(is_about_passed=True,
                                      is_unread=True,
                                      is_notified=False)
                              .count()))
        self.assertEquals(0, len(self._get_unread(student_list_url)
                                 .assignments))
        self.doLogin(teacher1)
        assert len(self._get_unread(teacher_list_url).assignments) == 1
        self.doLogin(teacher2)
        assert len(self._get_unread(teacher_list_url).assignments) == 1
        # Read message
        self.client.get(teacher_url)
        assert len(self._get_unread(teacher_list_url).assignments) == 0
        self.doLogin(teacher1)
        assert len(self._get_unread(teacher_list_url).assignments) == 1

        # One of teachers answered
        self.client.post(teacher_url, teacher_comment_dict)
        unread_msgs_for_student = (AssignmentNotification.objects
                              .filter(user=student,
                                      is_unread=True,
                                      is_notified=False)
                              .count())
        assert unread_msgs_for_student == 1
        self.doLogin(student)
        assert len(self._get_unread(student_list_url).assignments) == 1
        self.client.post(student_url, student_comment_dict)
        unread_msgs_for_teacher1 = (AssignmentNotification.objects
                                    .filter(is_about_passed=False,
                                            user=teacher1,
                                            is_unread=True,
                                            is_notified=False)
                                    .count())
        assert unread_msgs_for_teacher1 == 1


@pytest.mark.django_db
def test_notification_teachers_list_for_assignment(client):
    """On assignment creation we have to ensure that `notify_teachers`
    m2m prepopulated by course offering teachers with `notify_by_default=True`
    """
    student = StudentCenterFactory()
    t1, t2, t3, t4 = TeacherCenterFactory.create_batch(4)
    # Course offering with 4 teachers whom notify_by_default flag set to True
    co = CourseFactory.create(teachers=[t1, t2, t3, t4])
    co_teacher1 = CourseTeacher.objects.get(course=co, teacher=t1)
    co_teacher1.notify_by_default = False
    co_teacher1.save()
    EnrollmentFactory.create(student=student, course=co, grade=GradeTypes.good)
    # Create first assignment
    client.login(t1)
    a = AssignmentFactory.build()
    form = {
        'title': a.title,
        'is_online': 1,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
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
    assert not co.failed_by_student(student)
    client.login(student)
    sa = StudentAssignment.objects.get(assignment=assignment, student=student)
    sa_url = sa.get_student_url()
    client.post(sa_url, {'text': 'test first comment'})
    notifications = [n.user.pk for n in AssignmentNotification.objects.all()]
    # 1 - about assignment creation and 3 for teachers
    assert len(notifications) == 4
    assert t1.pk not in notifications
    AssignmentNotification.objects.all().delete()
    not_notify_teacher = assignment.notify_teachers.all()[0]
    assignment.notify_teachers.remove(not_notify_teacher)
    client.post(sa_url, {'text': 'second comment from student'})
    notifications = [n.user.pk for n in AssignmentNotification.objects.all()]
    assert len(notifications) == 2
    assert not_notify_teacher not in notifications


@pytest.mark.django_db
def test_notify_teachers_assignment_admin_form(client, curator):
    """`notify_teachers` should be prepopulated with course
    teachers if list is not specified manually"""
    from django.contrib.admin.sites import AdminSite
    t1, t2, t3, t4 = TeacherCenterFactory.create_batch(4)
    co = CourseFactory.create(teachers=[t1, t2, t3, t4])
    ma = AssignmentAdmin(Assignment, AdminSite())
    client.login(curator)
    a = AssignmentFactory.build()
    # Send data with empty notify_teachers list
    post_data = {
        'course': co.pk,
        'title': a.title,
        'is_online': 1,
        'text': a.text,
        'passing_score': 0,
        'maximum_score': 5,
        'deadline_at_0': str(a.deadline_at.date()),
        'deadline_at_1': '00:00'
    }
    response = client.post(reverse('admin:learning_assignment_add'), post_data)
    assert (Assignment.objects.count() == 1)
    assert len(Assignment.objects.order_by('id').all()[0].notify_teachers.all()) == 4
    # Manually select teachers from list
    co_t1, co_t2, co_t3, co_t4 = CourseTeacher.objects.filter(course=co).all()
    post_data['notify_teachers'] = [co_t1.pk, co_t2.pk]
    response = client.post(reverse('admin:learning_assignment_add'), post_data)
    assert (Assignment.objects.count() == 2)
    assert len(Assignment.objects.order_by('id').all()[0].notify_teachers.all()) == 4
    assert len(Assignment.objects.order_by('id').all()[1].notify_teachers.all()) == 2
    assert co_t3.pk not in Assignment.objects.order_by('id').all()[1].notify_teachers.all()


@pytest.mark.django_db
def test_new_assignment_notifications(settings):
    co = CourseFactory()
    enrollments = EnrollmentFactory.create_batch(5, course=co)
    assignment = AssignmentFactory(course=co)
    assert AssignmentNotification.objects.count() == 5
    enrollment = enrollments[0]
    enrollment.is_deleted = True
    enrollment.save()
    AssignmentNotification.objects.all().delete()
    assert AssignmentNotification.objects.count() == 0
    assignment = AssignmentFactory(course=co)
    assert AssignmentNotification.objects.count() == 4
    # Don't create new assignment for expelled students
    student = enrollments[1].student
    student.status = StudentStatuses.EXPELLED
    student.save()
    AssignmentNotification.objects.all().delete()
    assignment = AssignmentFactory(course=co)
    assert AssignmentNotification.objects.count() == 3


@pytest.mark.django_db
def test_new_assignment_timezone(settings):
    settings.LANGUAGE_CODE = 'ru'
    sa = StudentAssignmentFactory(assignment__course__city_id='spb')
    assignment = sa.assignment
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment.deadline_at = dt
    assignment.save()
    dt_local = assignment.deadline_at_local()
    assert dt_local.hour == 18
    dt_str = "18:00 04 февраля"
    AssignmentNotificationFactory(is_about_creation=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert dt_str in mail.outbox[0].body
    # Test with another timezone
    sa.assignment.course.city_id = 'nsk'
    sa.assignment.course.save()
    AssignmentNotificationFactory(is_about_creation=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert "22:00 04 февраля" in mail.outbox[0].body


@pytest.mark.django_db
def test_create_deadline_change_notification(settings):
    co = CourseFactory(city_id='spb')
    e1, e2 = EnrollmentFactory.create_batch(2, course=co)
    s1 = e1.student
    s1.status = StudentStatuses.EXPELLED
    s1.save()
    a = AssignmentFactory(course=co)
    assert AssignmentNotification.objects.count() == 1
    # Expellee has no StudentAssignment model
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    a.deadline_at = dt
    a.save()
    assert AssignmentNotification.objects.count() == 2


@pytest.mark.django_db
def test_deadline_changed_timezone(settings):
    settings.LANGUAGE_CODE = 'ru'
    sa = StudentAssignmentFactory(assignment__course__city_id='spb')
    assignment = sa.assignment
    dt = datetime.datetime(2017, 2, 4, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment.deadline_at = dt
    assignment.save()
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
    # Test with other timezone
    sa.assignment.course.city_id = 'nsk'
    sa.assignment.course.save()
    AssignmentNotificationFactory(is_about_deadline=True, user=sa.student,
                                  student_assignment=sa)
    out = StringIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert "22:00 04 февраля" in mail.outbox[0].body