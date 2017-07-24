# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import django_filters
from django.utils.translation import ugettext_lazy as _

EMPTY_CHOICE = ('', _('---------'))


class FilterEmptyChoiceMixin(object):
    """add empty choice to all choice fields"""
    def __init__(self, *args, **kwargs):
        super(FilterEmptyChoiceMixin, self).__init__(*args, **kwargs)

        choices = filter(
            lambda f: isinstance(self.filters[f], django_filters.ChoiceFilter),
            self.filters)
        for field_name in choices:
            extended_choices = ([EMPTY_CHOICE] +
                                self.filters[field_name].extra['choices'])
            self.filters[field_name].extra['choices'] = extended_choices
