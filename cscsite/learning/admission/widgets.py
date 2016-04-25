# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from itertools import chain

from django.core.urlresolvers import reverse
from django.forms import Textarea, Select
from django.forms.utils import flatatt
from django.utils.html import format_html
from django.utils.safestring import mark_safe


# Note: Not sure about this code, but it work's.
# May be broken on py3 due to encoding magic
class SimpleJSONWidget(Textarea):
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        else:
            value = value.decode('unicode-escape').encode('utf8')
        final_attrs = self.build_attrs(attrs, name=name)
        return format_html('<textarea{}>\r\n{}</textarea>',
                           flatatt(final_attrs),
                           mark_safe(value))
