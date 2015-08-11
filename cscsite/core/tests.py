# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from StringIO import StringIO

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from testfixtures import LogCapture
from mock import Mock

from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification
from learning.factories import AssignmentNotificationFactory, \
    CourseOfferingNewsNotificationFactory, AssignmentStudentFactory

from .management.commands.notify import Command
from .models import related_spec_to_list, apply_related_spec


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
        out = StringIO()
        mail.outbox = []
        Command().execute(stdout=out)
        self.assertEqual(0, len(mail.outbox))
        self.assertEqual(0, len(out.getvalue()))

        out = StringIO()
        mail.outbox = []
        an = AssignmentNotificationFactory.create(is_about_passed=True)
        Command().execute(stdout=out)
        self.assertEqual(1, len(mail.outbox))
        self.assertTrue(AssignmentNotification.objects
                        .get(pk=an.pk)
                        .is_notified)
        self.assertIn(reverse('a_s_detail_teacher',
                              args=[an.assignment_student.pk]),
                      mail.outbox[0].body)
        self.assertIn("sending notification for", out.getvalue())

        out = StringIO()
        mail.outbox = []
        Command().execute(stdout=out)
        self.assertEqual(0, len(mail.outbox))
        self.assertEqual(0, len(out.getvalue()))

        out = StringIO()
        mail.outbox = []
        conn = CourseOfferingNewsNotificationFactory.create()
        course_offering = conn.course_offering_news.course_offering
        Command().execute(stdout=out)
        self.assertEqual(1, len(mail.outbox))
        self.assertTrue(CourseOfferingNewsNotification.objects
                        .get(pk=an.pk)
                        .is_notified)
        self.assertIn(reverse('course_offering_detail',
                              args=[course_offering.course.slug,
                                    course_offering.semester.slug]),
                      mail.outbox[0].body)
        self.assertIn("sending notification for", out.getvalue())


class RelatedSpec(TestCase):
    def test_to_list(self):
        spec_form = [('assignment_student',
                      [('assignment',
                        [('course_offering', ['semester', 'course'])]),
                       'student'])]
        list_form \
            = ['assignment_student',
               'assignment_student__assignment',
               'assignment_student__assignment__course_offering',
               'assignment_student__assignment__course_offering__semester',
               'assignment_student__assignment__course_offering__course',
               'assignment_student__student']
        self.assertEqual(list_form, related_spec_to_list(spec_form))

        spec_form = [('assignment_student',
                      [('assignment',
                        [('course_offering', ['semester', 'course'])])]),
                     'student']
        list_form \
            = ['assignment_student',
               'assignment_student__assignment',
               'assignment_student__assignment__course_offering',
               'assignment_student__assignment__course_offering__semester',
               'assignment_student__assignment__course_offering__course',
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
