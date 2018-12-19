# -*- coding: utf-8 -*-
from django.test import TestCase

from learning.utils import split_on_condition


class UtilTests(TestCase):
    def test_split_list(self):
        xs = [1, 2, 3, 4]
        self.assertEqual(([1, 3], [2, 4]),
                          split_on_condition(xs, lambda x: x % 2 != 0))
        self.assertEqual((xs, []), split_on_condition(xs, lambda x: True))
        self.assertEqual(([], xs), split_on_condition(xs, lambda x: False))
