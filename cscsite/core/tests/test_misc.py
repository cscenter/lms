# -*- coding: utf-8 -*-

import pytest
import six

from io import StringIO as OutputIO
from mock import Mock

from django.core import mail, management

from django.urls import reverse
from django.test import TestCase

from learning.settings import PARTICIPANT_GROUPS
from users.factories import UserFactory

from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification
from learning.factories import AssignmentNotificationFactory, \
    CourseNewsNotificationFactory, StudentAssignmentFactory

from core.management.commands.notify import Command, get_base_url
from core.models import related_spec_to_list, apply_related_spec


# courtesy of SO http://stackoverflow.com/a/1305682/275084
class FakeObj(object):
    def __init__(self, d):
        for key, val in d.items():
            if isinstance(val, (list, tuple)):
                attr = [FakeObj(x) if isinstance(x, dict) else x
                        for x in val]
                setattr(self, key, attr)
            else:
                attr = FakeObj(val) if isinstance(val, dict) else val
                setattr(self, key, attr)


class NotifyCommandTest(TestCase):
    def test_notifications(self):
        out = OutputIO()
        mail.outbox = []
        management.call_command("notify", stdout=out)
        self.assertEqual(0, len(mail.outbox))
        self.assertEqual(0, len(out.getvalue()))

        out = OutputIO()
        mail.outbox = []
        an = AssignmentNotificationFactory.create(is_about_passed=True)
        management.call_command("notify", stdout=out)
        self.assertEqual(1, len(mail.outbox))
        self.assertTrue(AssignmentNotification.objects
                        .get(pk=an.pk)
                        .is_notified)
        self.assertIn(an.student_assignment.get_teacher_url(),
                      mail.outbox[0].body)
        self.assertIn("sending notification for", out.getvalue())

        out = OutputIO()
        mail.outbox = []
        management.call_command("notify", stdout=out)
        self.assertEqual(0, len(mail.outbox))
        self.assertEqual(0, len(out.getvalue()))

        out = OutputIO()
        mail.outbox = []
        conn = CourseNewsNotificationFactory.create()
        course_offering = conn.course_offering_news.course_offering
        management.call_command("notify", stdout=out)
        self.assertEqual(1, len(mail.outbox))
        conn.refresh_from_db()
        assert conn.is_notified
        self.assertIn(course_offering.get_absolute_url(),
                      mail.outbox[0].body)
        self.assertIn("sending notification for", out.getvalue())


class RelatedSpec(TestCase):
    def test_to_list(self):
        spec_form = [('student_assignment',
                      [('assignment',
                        [('course_offering', ['semester', 'meta_course'])]),
                       'student'])]
        list_form \
            = ['student_assignment',
               'student_assignment__assignment',
               'student_assignment__assignment__course_offering',
               'student_assignment__assignment__course_offering__semester',
               'student_assignment__assignment__course_offering__meta_course',
               'student_assignment__student']
        self.assertEqual(list_form, related_spec_to_list(spec_form))

        spec_form = [('student_assignment',
                      [('assignment',
                        [('course_offering', ['semester', 'meta_course'])])]),
                     'student']
        list_form \
            = ['student_assignment',
               'student_assignment__assignment',
               'student_assignment__assignment__course_offering',
               'student_assignment__assignment__course_offering__semester',
               'student_assignment__assignment__course_offering__meta_course',
               'student']
        self.assertEqual(list_form, related_spec_to_list(spec_form))

    def test_apply(self):
        class FakeQS(object):
            def select_related(self, _):
                pass

            def prefetch_related(self, _):
                pass

        test_obj = FakeQS()
        test_obj.select_related = Mock(return_value=test_obj)
        test_obj.prefetch_related = Mock(return_value=test_obj)

        related_spec = {'select': [('foo', ['bar', 'baz'])],
                        'prefetch': ['baq']}
        list_select = ['foo', 'foo__bar', 'foo__baz']
        list_prefetch = ['baq']
        apply_related_spec(test_obj, related_spec)
        test_obj.select_related.assert_called_once_with(*list_select)
        test_obj.prefetch_related.assert_called_once_with(*list_prefetch)


@pytest.mark.django_db
def test_middleware_center_site(client, settings):
    """Make sure we have attached `city_code` attr to each request object"""
    assert settings.SITE_ID == settings.CENTER_SITE_ID
    url = reverse('index')
    response = client.get(url)
    assert hasattr(response.wsgi_request, 'city_code')
    assert response.wsgi_request.city_code == settings.DEFAULT_CITY_CODE


@pytest.mark.django_db
def test_get_base_url():
    """Site domain in notifications depends on recipient user groups"""
    user = UserFactory(groups=[PARTICIPANT_GROUPS.STUDENT_CENTER])
    notification = AssignmentNotificationFactory(user=user)
    assert get_base_url(notification) == "https://compscicenter.ru"
    user = UserFactory(groups=[PARTICIPANT_GROUPS.STUDENT_CENTER,
                               PARTICIPANT_GROUPS.STUDENT_CLUB])
    notification = AssignmentNotificationFactory(user=user)
    assert get_base_url(notification) == "https://compscicenter.ru"
    notification.user = UserFactory(groups=[PARTICIPANT_GROUPS.STUDENT_CLUB])
    assert get_base_url(notification) == "http://compsciclub.ru"
    notification.user = UserFactory(groups=[PARTICIPANT_GROUPS.STUDENT_CENTER,
                                            PARTICIPANT_GROUPS.TEACHER_CLUB])
    assert get_base_url(notification) == "https://compscicenter.ru"
    notification.user = UserFactory(groups=[PARTICIPANT_GROUPS.TEACHER_CLUB])
    assert get_base_url(notification) == "http://compsciclub.ru"
    notification.user = UserFactory(groups=[PARTICIPANT_GROUPS.TEACHER_CLUB,
                                            PARTICIPANT_GROUPS.GRADUATE_CENTER])
    assert get_base_url(notification) == "https://compscicenter.ru"
