# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.utils.encoding import smart_text

from testfixtures import LogCapture

from textpages.models import Textpage, CustomTextpage


PLACEHOLDER_FRAGMENT = "Please change this text"


class TextpagesTests(TestCase):
    def test_to_strings(self):
        test_page_fields = {'slug': "test_custom_textpage",
                            'name': "Custom textpage for testing",
                            'text': ("Some text for custom textpage, "
                                     "just in case; и юникод!")}
        tp = CustomTextpage(**test_page_fields)
        self.assertEqual(smart_text(tp), smart_text(test_page_fields['name']))
        obj = Textpage.objects.get(url_name='online')
        self.assertEqual(smart_text(obj), obj.name)

    def test_open_textpage(self):
        client = Client()
        resp = client.get(reverse('enrollment'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(PLACEHOLDER_FRAGMENT, resp.content)
        self.assertEqual(resp.context['object'],
                         Textpage.objects.get(url_name='enrollment'))

    def test_missing_open_textpage(self):
        client = Client()
        Textpage.objects.filter(url_name='online').delete()
        with LogCapture() as l:
            resp = client.get(reverse('online'))
            self.assertEqual(resp.status_code, 404)
            l.check(('textpages.views', 'WARNING',
                     "can't find \"online\" as a textpage"))
        resp = client.get(reverse('enrollment'))
        self.assertEqual(resp.status_code, 200)

    def test_custom_open_textpage(self):
        test_page_fields = {'slug': "test_custom_textpage",
                            'name': "Custom textpage for testing",
                            'text': ("Some text for custom textpage, "
                                     "just in case; и юникод!")}
        tp = CustomTextpage(**test_page_fields)
        tp.save()

        client = Client()
        resp = client.get(tp.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertIn(test_page_fields['text'], resp.content)
        self.assertEqual(resp.context['object'], tp)

    def test_missing_custom_open_textpage(self):
        client = Client()
        with LogCapture() as l:
            resp = client.get(reverse('custom_text_page', args=["foobar"]))
            self.assertEqual(resp.status_code, 404)
            l.check(('textpages.views', 'WARNING',
                     "can't find \"foobar\" as a custom textpage"))
