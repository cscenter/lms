from __future__ import unicode_literals

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils.encoding import smart_text
from django.utils.translation import get_language

from news.models import News
from news.factories import NewsFactory


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
        current_site = Site.objects.get(pk=settings.SITE_ID)

        news1 = NewsFactory(language=get_language(), site=current_site, published=False)
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [])
        news1.published = True
        news1.save()
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [news1])

        last3_news = NewsFactory.create_batch(3,
          language=get_language(), site=current_site, published=True)
        response = self.client.get(reverse('index'))
        self.assertEqual(len(response.context['news_objects']), 3)
        self.assertItemsEqual(response.context['news_objects'], last3_news)
        self.assertEqual(smart_text(response.content)
                         .count(last3_news[0].get_absolute_url()), 1)
