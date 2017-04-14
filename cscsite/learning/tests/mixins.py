# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.conf import settings
from django.urls import reverse
from django.conf.urls.static import static

import cscenter.urls


class MyUtilitiesMixin(object):
    def assertStatusCode(self, code, url_name, make_reverse=True, **kwargs):
        if make_reverse:
            url = reverse(url_name, **kwargs)
        else:
            url = url_name
        self.assertEqual(code, self.client.get(url).status_code)

    def assertLoginRedirect(self, url):
        self.assertRedirects(self.client.get(url),
                             "{}?next={}".format(settings.LOGIN_URL, url))

    def assertPOSTLoginRedirect(self, url, form):
        self.assertRedirects(self.client.post(url, form),
                             "{}?next={}".format(settings.LOGIN_URL, url))

    def assertSameObjects(self, obj_list1, obj_list2):
        self.assertEqual(set(obj_list1), set(obj_list2))

    def doLogin(self, user):
        self.assertTrue(self.client.login(username=user.username,
                                          password=user.raw_password))

    def doLogout(self):
        self.client.logout()

    def calendar_month_to_object_list(self, calendar_month):
        return [x
                for week in calendar_month
                for day in week[1]
                for x in day[1]]


class MediaServingMixin(object):
    def setUp(self):
        self._original_urls = cscenter.urls.urlpatterns
        with self.settings(DEBUG=True):
            s = static(settings.MEDIA_URL,
                       document_root=settings.MEDIA_ROOT)
            cscenter.urls.urlpatterns += s

    def tearDown(self):
        cscenter.urls.urlpatterns = self._original_urls
