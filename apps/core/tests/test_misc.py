# -*- coding: utf-8 -*-

from unittest.mock import Mock

import pytest
from core.tests.utils import CSCTestCase

from core.admin import related_spec_to_list, apply_related_spec
from core.urls import reverse


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


class RelatedSpec(CSCTestCase):
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

