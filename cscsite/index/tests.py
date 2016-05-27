from __future__ import unicode_literals

import unittest

from django.test import TestCase
from django.core.urlresolvers import reverse


class assertItemsEqualMixin(object):
    def assertItemsEqual(self, a, b):
        """
        This is needed because assertItemsEqual doesn't exist in Python 3
        """
        return self.assertEqual(len(set(a) ^ set(b)), 0)


class IndexTests(assertItemsEqualMixin, TestCase):
    fixtures = ['cscenter_htmlpages.json']

    @unittest.skip('removed from urls.py')
    def test_no_news(self):
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [])
        # Assuming that there is no translation in tests
        self.assertEqual(response.content.count(b"All news"), 0)
        self.assertEqual(response.content.count(b"No news yet"), 1)

    def test_no_menu_highlight(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.content.count(b"current"), 0)
