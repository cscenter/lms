# -*- coding: utf-8 -*-

from io import StringIO as OutputIO

import pytest
from django.core import mail, management
from django.test import TestCase
from django.urls import reverse
from mock import Mock

from core.management.commands.notify import get_base_url
from core.admin import related_spec_to_list, apply_related_spec
from learning.factories import AssignmentNotificationFactory, \
    CourseNewsNotificationFactory
from learning.models import AssignmentNotification
from users.settings import AcademicRoles
from users.factories import UserFactory


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
        course = conn.course_offering_news.course
        management.call_command("notify", stdout=out)
        self.assertEqual(1, len(mail.outbox))
        conn.refresh_from_db()
        assert conn.is_notified
        self.assertIn(course.get_absolute_url(),
                      mail.outbox[0].body)
        self.assertIn("sending notification for", out.getvalue())


class RelatedSpec(TestCase):
    def test_to_list(self):
        spec_form = [('student_assignment',
                      [('assignment',
                        [('course', ['semester', 'meta_course'])]),
                       'student'])]
        list_form \
            = ['student_assignment',
               'student_assignment__assignment',
               'student_assignment__assignment__course',
               'student_assignment__assignment__course__semester',
               'student_assignment__assignment__course__meta_course',
               'student_assignment__student']
        self.assertEqual(list_form, related_spec_to_list(spec_form))

        spec_form = [('student_assignment',
                      [('assignment',
                        [('course', ['semester', 'meta_course'])])]),
                     'student']
        list_form \
            = ['student_assignment',
               'student_assignment__assignment',
               'student_assignment__assignment__course',
               'student_assignment__assignment__course__semester',
               'student_assignment__assignment__course__meta_course',
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
    user = UserFactory(groups=[AcademicRoles.STUDENT_CENTER])
    notification = AssignmentNotificationFactory(user=user)
    assert get_base_url(notification) == "https://compscicenter.ru"
    user = UserFactory(groups=[AcademicRoles.STUDENT_CENTER,
                               AcademicRoles.STUDENT_CLUB])
    notification = AssignmentNotificationFactory(user=user)
    assert get_base_url(notification) == "https://compscicenter.ru"
    notification.user = UserFactory(groups=[AcademicRoles.STUDENT_CLUB])
    assert get_base_url(notification) == "http://compsciclub.ru"
    notification.user = UserFactory(groups=[AcademicRoles.STUDENT_CENTER,
                                            AcademicRoles.TEACHER_CLUB])
    assert get_base_url(notification) == "https://compscicenter.ru"
    notification.user = UserFactory(groups=[AcademicRoles.TEACHER_CLUB])
    assert get_base_url(notification) == "http://compsciclub.ru"
    notification.user = UserFactory(groups=[AcademicRoles.TEACHER_CLUB,
                                            AcademicRoles.GRADUATE_CENTER])
    assert get_base_url(notification) == "https://compscicenter.ru"
