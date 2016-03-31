# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import pytest
import logging
import os

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from testfixtures import LogCapture

from django.conf import settings
from django.conf.urls.static import static
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test.utils import override_settings
from django.test import TestCase
from django.utils.encoding import smart_text

import cscenter.urls
from learning.admin import AssignmentAdmin
from learning.utils import get_current_semester_pair
from learning.models import AssignmentNotification
from ..factories import *
from .mixins import *


class NotificationTests(MyUtilitiesMixin, TestCase):
    def _get_unread(self, url):
        return (self.client.get(url)
                .context['request']
                .unread_notifications_cache)

    def test_assignment(self):
        student = UserFactory.create(groups=['Student [CENTER]'])
        teacher1 = UserFactory.create(groups=['Teacher [CENTER]'])
        teacher2 = UserFactory.create(groups=['Teacher [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher1, teacher2])
        EnrollmentFactory.create(student=student, course_offering=co)
        # Notify_teachers m2m populated only from view action
        self.doLogin(teacher1)
        a = AssignmentFactory.build()
        form = {'title': a.title,
                'is_online': 1,
                'text': a.text,
                'grade_min': 0,
                'grade_max': 5,
                'deadline_at_0': str(a.deadline_at.date()),
                'deadline_at_1': '00:00'
        }
        url = reverse('assignment_add', args=[co.course.slug, co.semester.slug])
        response = self.client.post(url, form, follow=True)
        assert response.status_code == 200
        assignments = co.assignment_set.all()
        assert len(assignments) == 1
        a = assignments[0]
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        student_url = reverse('a_s_detail_student', args=[a_s.pk])
        teacher_url = reverse('a_s_detail_teacher', args=[a_s.pk])
        student_list_url = reverse('assignment_list_student', args=[])
        teacher_list_url = reverse('assignment_list_teacher', args=[])
        student_comment_dict = {'text': "Test student comment without file"}
        teacher_comment_dict = {'text': "Test teacher comment without file"}

        # Post first comment on assignment
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
def test_notification_teachers_list_for_assignment(client,
                                                   teacher_center_factory,
                                                   student_factory):
    """After assignment creation we must be sure that `notify_teachers`
    m2m prepopulated with course offering teachers whom notify_by_default flag is set.
    """
    student = student_factory()
    t1, t2, t3, t4 = teacher_center_factory.create_batch(4)
    # Course offering with 4 teachers whom notify_by_default flag set to True
    co = CourseOfferingFactory.create(teachers=[t1, t2, t3, t4])
    co_teacher1 = CourseOfferingTeacher.objects.get(course_offering=co, teacher=t1)
    co_teacher1.notify_by_default = False
    co_teacher1.save()
    EnrollmentFactory.create(student=student, course_offering=co)
    # Create first assignment
    client.login(t1)
    a = AssignmentFactory.build()
    form = {
        'title': a.title,
        'is_online': 1,
        'text': a.text,
        'grade_min': 0,
        'grade_max': 5,
        'deadline_at_0': str(a.deadline_at.date()),
        'deadline_at_1': '00:00'
    }
    url = reverse('assignment_add', args=[co.course.slug, co.semester.slug])
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    assignments = co.assignment_set.all()
    assert len(assignments) == 1
    assignment = assignments[0]
    assert len(assignment.notify_teachers.all()) == 3
    # Update assignment and check, that notify_teachers list not changed
    form['grade_max'] = 10
    url = reverse('assignment_edit', args=[co.course.slug, co.semester.slug, assignment.pk])
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    assert len(assignment.notify_teachers.all()) == 3
    # Leave a comment from student
    client.login(student)
    sa = StudentAssignment.objects.get(assignment=assignment, student=student)
    sa_url = reverse('a_s_detail_student', args=[sa.pk])
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
def test_notify_teachers_assignment_admin_form(client, curator,
                                               teacher_center_factory):
    """`notify_teachers` should be prepopulated with course offering
    teachers if list is not specified manually"""
    from django.contrib.admin.sites import AdminSite
    t1, t2, t3, t4 = teacher_center_factory.create_batch(4)
    co = CourseOfferingFactory.create(teachers=[t1, t2, t3, t4])
    ma = AssignmentAdmin(Assignment, AdminSite())
    client.login(curator)
    a = AssignmentFactory.build()
    # Send data with empty notify_teachers list
    post_data = {
        'course_offering': co.pk,
        'title': a.title,
        'is_online': 1,
        'text': a.text,
        'grade_min': 0,
        'grade_max': 5,
        'deadline_at_0': str(a.deadline_at.date()),
        'deadline_at_1': '00:00'
    }
    response = client.post(reverse('admin:learning_assignment_add'), post_data)
    assert (Assignment.objects.count() == 1)
    assert len(Assignment.objects.order_by('id').all()[0].notify_teachers.all()) == 4
    # Manually select teachers from list
    post_data['notify_teachers'] = [t1.pk, t2.pk]
    response = client.post(reverse('admin:learning_assignment_add'), post_data)
    assert (Assignment.objects.count() == 2)
    assert len(Assignment.objects.order_by('id').all()[0].notify_teachers.all()) == 4
    assert len(Assignment.objects.order_by('id').all()[1].notify_teachers.all()) == 2
    assert t3.pk not in Assignment.objects.order_by('id').all()[1].notify_teachers.all()