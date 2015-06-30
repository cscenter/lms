from __future__ import unicode_literals

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from news.models import News


class assertItemsEqualMixin(object):
    def assertItemsEqual(self, a, b):
        """
        This is needed because assertItemsEqual doesn't exist in Python 3
        """
        return self.assertEqual(len(set(a) ^ set(b)), 0)


class IndexTests(assertItemsEqualMixin, TestCase):
    fixtures = ['cscenter_htmlpages.json']

    def test_no_news(self):
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [])
        # Assuming that there is no translation in tests
        self.assertEqual(response.content.count(b"All news"), 0)
        self.assertEqual(response.content.count(b"No news yet"), 1)

    def test_no_menu_highlight(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.content.count(b"current"), 0)

    def test_news(self):
        News1 = News(title="FooBarUniqueNews1",
                     slug="foo-bar-unique-1",
                     published=False)
        News1.save()
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [])
        News1.published = True
        News1.save()
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [News1])
        News2 = News(title="FooBarUniqueNews2",
                     slug="foo-bar-unique-2",
                     published=True)
        News3 = News(title="FooBarUniqueNews3",
                     slug="foo-bar-unique-3",
                     published=True)
        News4 = News(title="FooBarUniqueNews4",
                     slug="foo-bar-unique-4",
                     published=True)
        News2.save()
        News3.save()
        News4.save()
        response = self.client.get(reverse('index'))
        self.assertEqual(len(response.context['news_objects']), 3)
        self.assertItemsEqual(response.context['news_objects'],
                              [News2, News3, News4])
        self.assertEqual(response.content.count(b"FooBarUniqueNews3"), 1)
        self.assertEqual(smart_text(response.content)
                         .count(News3.get_absolute_url()), 1)
