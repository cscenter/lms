from __future__ import unicode_literals

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
                                  sites=(current_site,),
                                  published=True)
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 1)
        news_detail_url = reverse('news_detail', kwargs={'slug': news.slug})
        self.assertEquals(200, self.client.get(news_detail_url).status_code)

        # Trying to get first news in other language
        # TODO: uncomment after delete LANGUAGE_CODE from test.py settings
        # and fixing all crushed tests
        # with translation.override(next_language):
        #     news_url_other_lang = reverse('news_detail', kwargs={'slug': news.slug})
        #     self.assertEquals(404, self.client.get(news_url_other_lang).status_code)
        
        # Add news to other site
        news2 = NewsFactory.create(language=current_language,
                                   sites=(other_site,),
                                   published=True)
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 1)
        news_other_url = reverse('news_detail', kwargs={'slug': news2.slug})
        self.assertEquals(404, self.client.get(news_other_url).status_code)
        # Add news to both sites
        news_common = NewsFactory.create(language=current_language, sites=sites,
                                         published=True)
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 2)
        news_common_url = reverse('news_detail', kwargs={'slug': news_common.slug})
        self.assertEquals(200, self.client.get(news_common_url).status_code)
        # Change language for common_news
        news_common.language = next_language
        news_common.save()
        response = self.client.get(reverse('news_list'))
        self.assertEqual(len(response.context['object_list']), 1)




        

        # news1.published = True
        # news1.save()
        # response = self.client.get(reverse('index'))
        # self.assertItemsEqual(response.context['news_objects'], [news1])

        # last3_news = NewsFactory.create_batch(3,
        #   language=get_language(), sites=(current_site,), published=True)
        # response = self.client.get(reverse('index'))
        # self.assertEqual(len(response.context['news_objects']), 3)
        # self.assertItemsEqual(response.context['news_objects'], last3_news)
        # self.assertEqual(smart_text(response.content)
        #                  .count(last3_news[0].get_absolute_url()), 1)
