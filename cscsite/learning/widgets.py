from django.forms.utils import to_current_timezone
from django.utils.translation import ugettext_lazy as _
from floppyforms import __future__ as forms


class DateInputAsTextInput(forms.DateInput):
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        super(DateInputAsTextInput, self).__init__(attrs, format)
        self.format = '%d.%m.%Y'


class CustomSplitDateTimeWidget(forms.MultiWidget):
    """Using bootstrap datetime picker for assignment form"""
    supports_microseconds = False

    def __init__(self, attrs=None, date_format=None, time_format=None):
        date_attrs = attrs or {}
        date_attrs['class'] = 'datepicker'
        widgets = (DateInputAsTextInput(attrs=date_attrs),
                   forms.TimeInput(attrs=attrs, format=time_format))
        super(CustomSplitDateTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]

    def format_output(self, rendered_widgets):
        return ("""
        <div class="row">
            <div class="col-xs-6">
                <div class="input-group">
                    <span class="input-group-addon">
                        <i class="fa fa-calendar"></i>
                    </span>
                    {0}
                </div>
                <span class="help-block">{format}: dd.mm.yyyy</span>
            </div>
            <div class="col-xs-6">
                <div class="input-group">
                    <span class="input-group-addon">
                        <i class="fa fa-clock-o"></i>
                    </span>
                    {1}
                </div>
            </div>
        </div>""".format(*rendered_widgets, format=_("Format")))