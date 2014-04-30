from __future__ import absolute_import

from django.test import TestCase

from testfixtures import LogCapture

from .templatetags.navigation import current


# courtesy of SO http://stackoverflow.com/a/1305682/275084
class FakeObj(object):
    def __init__(self, d):
        for key, val in d.items():
            if isinstance(val, (list, tuple)):
                attr = [FakeObj(x) if isinstance(x, dict) else x
                        for x in val]
                setattr(self, key, attr)
            else:
                attr = FakeObj(val) if isinstance(val, dict) else val
                setattr(self, key, attr)


class CurrentTagTest(TestCase):
    """
    Verify that "current" template tag works
    """
    def test_current(self):
        test_settings = {'first_page': {},
                         'second_page': {},
                         'second_subpage': {'parent': 'second_page'},
                         'second_page_alias': {'alias': 'second_page'},
                         'second_subpage_alias': {'alias': 'second_subpage'},
                         'second_subpage_another_alias':
                         {'alias': 'second_subpage'},
                         'second_subpage_alias_alias':
                         {'alias': 'second_subpage_alias'},
                         'dangling_subpage': {'parent': 'nonexistent_page'}}

        test_ret = 'test_return'

        def fake_context(url_name):
            return {'request': FakeObj({'resolver_match':
                                        {'url_name': url_name}})}

        def call_current(current_url_name, tag_url_name):
            ret = current(fake_context(current_url_name),
                          tag_url_name, return_value=test_ret)
            self.assertIn(ret, [test_ret, ''])
            return ret == test_ret

        with self.settings(MENU_URL_NAMES=test_settings):
            # basic stuff
            self.assertTrue(call_current('first_page', 'first_page'))
            self.assertFalse(call_current('first_page', 'second_page'))
            self.assertFalse(call_current('second_page', 'first_page'))

            # logging and unexpected URL names
            with LogCapture() as l:
                self.assertTrue(call_current('some_page', 'some_page'))
                self.assertFalse(call_current('some_other_page', 'some_page'))
                self.assertFalse(call_current('some_page', 'some_other_page'))
                l.check(('core.templatetags.navigation', 'WARNING',
                         "can't find url some_page in MENU_URL_NAMES"),
                        ('core.templatetags.navigation', 'WARNING',
                         "can't find url some_other_page in MENU_URL_NAMES"),
                        ('core.templatetags.navigation', 'WARNING',
                         "can't find url some_page in MENU_URL_NAMES"))

            # dangling subpage with no info on parent
            with LogCapture() as l:
                self.assertTrue(call_current('dangling_subpage',
                                             'dangling_subpage'))
                self.assertTrue(call_current('dangling_subpage',
                                             'nonexistent_page'))
                self.assertFalse(call_current('nonexistent_page',
                                              'dangling_subpage'))
                l.check(('core.templatetags.navigation', 'WARNING',
                         "can't find url nonexistent_page in MENU_URL_NAMES"),
                        ('core.templatetags.navigation', 'WARNING',
                         "can't find url nonexistent_page in MENU_URL_NAMES"))

            # parents
            self.assertTrue(call_current('second_page', 'second_page'))
            self.assertTrue(call_current('second_subpage', 'second_page'))
            self.assertFalse(call_current('second_subpage', 'first_page'))
            self.assertFalse(call_current('second_subpage', 'some_page'))

            # aliases
            self.assertTrue(call_current('second_page_alias', 'second_page'))
            self.assertFalse(call_current('second_page_alias', 'first_page'))
            self.assertFalse(call_current('second_page', 'second_page_alias'))

            self.assertTrue(call_current('second_subpage_alias',
                                         'second_page'))
            self.assertTrue(call_current('second_subpage_alias',
                                         'second_subpage'))
            self.assertTrue(call_current('second_subpage_alias',
                                         'second_subpage_alias'))
            self.assertFalse(call_current('second_subpage_alias',
                                          'first_page'))
            self.assertFalse(call_current('second_page',
                                          'second_subpage_alias'))
            self.assertFalse(call_current('second_subpage',
                                          'second_subpage_alias'))

            self.assertTrue(call_current('second_subpage_alias_alias',
                                         'second_page'))
            self.assertTrue(call_current('second_subpage_alias_alias',
                                         'second_subpage'))
            self.assertTrue(call_current('second_subpage_alias_alias',
                                         'second_subpage_alias'))

            self.assertTrue(call_current('second_subpage_another_alias',
                                         'second_page'))
            self.assertTrue(call_current('second_subpage_another_alias',
                                         'second_subpage'))
            self.assertFalse(call_current('second_subpage_another_alias',
                                          'second_subpage_alias'))
