from django.test import TestCase
from django.core.urlresolvers import reverse

from news.models import News

class IndexTests(TestCase):
    def test_no_news(self):
        response = self.client.get(reverse('index'))
        self.assertItemsEqual(response.context['news_objects'], [])
        # Assuming that there is no translation in tests
        self.assertEqual(response.content.count("All news"), 0)
        self.assertEqual(response.content.count("No news yet"), 1)

    def test_no_menu_highlight(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.content.count("current"), 0)

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
        self.assertEqual(response.content.count("FooBarUniqueNews3"), 1)
        self.assertEqual(response.content.count(News3.get_absolute_url()), 1)
