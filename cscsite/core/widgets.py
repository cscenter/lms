# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

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
