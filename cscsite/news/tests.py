from __future__ import unicode_literals

import unittest

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils.encoding import smart_text
from django.utils import translation
from django.utils.translation import get_language, activate

from .models import News
from .factories import NewsFactory



class NewsTests(TestCase):

    @unittest.skip('removed from urls.py')
    def test_sites(self):
        """Test news separation by site_id"""
        cscenter_site = Site.objects.get(domain='compscicenter.ru')
        csclub_site = Site.objects.get(domain='compsciclub.ru')
        sites = (cscenter_site, csclub_site)
        if settings.SITE_ID == cscenter_site.id:
            current_site = cscenter_site
        elif settings.SITE_ID == csclub_site.id:
            current_site = csclub_site
        # Get site distinct from current one
        # FIXME: Mb it would be useful to rewrite like util function
        for site in sites:
            if site != current_site:
                other_site = site
        self.assertIsNotNone(other_site)

        current_language = get_language()
        languages = [code for code, name in settings.LANGUAGES]
        for lang in languages:
            if lang != current_language:
                next_language = lang
        self.assertIsNotNone(next_language)

        self.assertIsNotNone(current_site)
        news = NewsFactory.create(language=current_language,
                                  site=current_site,
                                  published=True)
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 1)
        news_detail_url = reverse('news_detail', kwargs={'slug': news.slug})
        self.assertEquals(200, self.client.get(news_detail_url).status_code)
        # Change language
        news.language = next_language
        news.save()
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 0)
        # Revert back language
        news.language = current_language
        news.save()

        # Trying to get first news in other language
        # TODO: uncomment after delete LANGUAGE_CODE from test.py settings
        # and fixing all crushed tests
        # with translation.override(next_language):
        #     news_url_other_lang = reverse('news_detail', kwargs={'slug': news.slug})
        #     self.assertEquals(404, self.client.get(news_url_other_lang).status_code)
        
        # Add news to other site
        news2 = NewsFactory.create(language=current_language,
                                   site=other_site,
                                   published=True)
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 1)
        news_other_url = reverse('news_detail', kwargs={'slug': news2.slug})
        self.assertEquals(404, self.client.get(news_other_url).status_code)
