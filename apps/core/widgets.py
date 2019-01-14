from django import forms
from django_filters.widgets import RangeWidget

from core.timezone import city_aware_to_naive
from core.constants import DATE_FORMAT_RU


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
