# -*- coding: utf-8 -*-

from collections import OrderedDict, namedtuple
from typing import NamedTuple, Callable

from django import forms
from django.utils.translation import ugettext_lazy as _
from django_filters.widgets import RangeWidget, SuffixedMultiWidget

from core.admin import city_aware_to_naive
from learning.settings import DATE_FORMAT_RU


class UbereditorWidget(forms.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super().__init__(*args, **kwargs)


class AdminRichTextAreaWidget(UbereditorWidget):
    template_name = 'widgets/ubertextarea.html'


class DateTimeRangeWidget(RangeWidget):
    template_name = 'widgets/datetime_range.html'
    suffixes = ['from', 'to']

    def __init__(self, attrs=None):
        widgets = (forms.DateInput(attrs={"class": "form-control",
                                          "autocomplete": "off",
                                          "placeholder": "C"}),
                   forms.DateInput(attrs={"class": "form-control",
                                          "autocomplete": "off",
                                          "placeholder": "По"}))
        super(RangeWidget, self).__init__(widgets, attrs)


class Tab(NamedTuple):
    target: str
    name: str
    exists: Callable = lambda: False
    visible: bool = False
    unread_cnt: bool = 0


class TabbedPane:
    def __init__(self):
        self._tabs = {}
        self._active_tab = None

    def add(self, tab):
        if not isinstance(tab, Tab):
            raise TypeError("Provide an instance of Tab")
        if not tab.exists:
            tab.visible = False
        self._tabs[tab.target] = tab

    def set_active_tab(self, tab):
        if tab.target not in self._tabs or not self._tabs[tab.target].visible:
            raise ValueError(f"Can't' set tab {tab} as active")
        self._active_tab = tab

    @property
    def active_tab(self):
        return self._active_tab

    def __iter__(self):
        return iter(self._tabs.items())

    def __getitem__(self, item):
        return self._tabs[item]


class DateInputAsTextInput(forms.DateInput):
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        super(DateInputAsTextInput, self).__init__(attrs, format)
        self.format = DATE_FORMAT_RU


class TimeInputAsTextInput(forms.TimeInput):
    input_type = 'text'


class CityAwareSplitDateTimeWidget(forms.MultiWidget):
    """Using bootstrap datetime picker for assignment form"""
    supports_microseconds = False
    template_name = "widgets/city_aware_split_datetime.html"

    def __init__(self, attrs=None, date_format=None, time_format=None):
        attrs = {"class": "form-control"}
        widgets = (
            DateInputAsTextInput(attrs=attrs, format=date_format),
            TimeInputAsTextInput(attrs=attrs, format=time_format),
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            value = city_aware_to_naive(value, self.instance)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]
