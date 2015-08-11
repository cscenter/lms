# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

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
        a = AssignmentFactory.create(course_offering=co)
        a_s = (AssignmentStudent.objects
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
        self.assertEquals(1, len(self._get_unread(teacher_list_url)
                                 .assignments))
        self.doLogin(teacher2)
        self.assertEquals(1, len(self._get_unread(teacher_list_url)
                                 .assignments))
        self.client.get(teacher_url)
        self.assertEquals(0, len(self._get_unread(teacher_list_url)
                                 .assignments))
        self.doLogin(teacher1)
        self.assertEquals(1, len(self._get_unread(teacher_list_url)
                                 .assignments))

        # One of teachers answered
        self.doLogin(teacher1)
        self.client.post(teacher_url, teacher_comment_dict)
        self.assertEquals(1, (AssignmentNotification.objects
                              .filter(user=student,
                                      is_unread=True,
                                      is_notified=False)
                              .count()))
        self.doLogin(student)
        self.assertEquals(1, len(self._get_unread(student_list_url)
                                 .assignments))
        self.client.post(student_url, student_comment_dict)
        self.assertEquals(1, (AssignmentNotification.objects
                              .filter(is_about_passed=False,
                                      user=teacher1,
                                      is_unread=True,
                                      is_notified=False)
                              .count()))
