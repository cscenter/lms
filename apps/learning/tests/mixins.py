# -*- coding: utf-8 -*-

from core.urls import reverse

__all__ = ('MyUtilitiesMixin',)


# FIXME: rewrite tests with pytest and remove this mixin.
# XXX: assertion for redirects duplicated in conftest.py
class MyUtilitiesMixin:
    def assertStatusCode(self, code, url_name, make_reverse=True, **kwargs):
        if make_reverse:
            url = reverse(url_name, **kwargs)
        else:
            url = url_name
        self.assertEqual(code, self.client.get(url).status_code)

    def assertSameObjects(self, obj_list1, obj_list2):
        self.assertEqual(set(obj_list1), set(obj_list2))

    def doLogin(self, user):
        self.assertTrue(self.client.login(user))

    def doLogout(self):
        self.client.logout()
