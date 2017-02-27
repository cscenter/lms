# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from collections import MutableMapping, OrderedDict, namedtuple

from django_filters.widgets import RangeWidget


class DateTimeRangeWidget(RangeWidget):
    def format_output(self, rendered_widgets):
        return """
        <div class="input-daterange">
            <div class="input-group">
                <span class="input-group-addon">
                    <i class="fa fa-calendar" aria-hidden="true"></i>
                </span>
                {}
            </div>
            <div class="input-group">
                <span class="input-group-addon">-</span>
                {}
            </div>
        </div>
        """.format(rendered_widgets[0], rendered_widgets[1])


Tab = namedtuple('Tab', ['target', 'name', 'show', 'badge'])
Tab.__new__.__defaults__ = (None,) * len(Tab._fields)


class TabbedPane(OrderedDict):
    def __setitem__(self, key, value, *args, **kwargs):
        raise TypeError("Direct assignment not allowed")

    def add(self, tab):
        if not isinstance(tab, Tab):
            raise TypeError("Provide an instance of Tab")
        OrderedDict.__setitem__(self, tab.target, tab)
