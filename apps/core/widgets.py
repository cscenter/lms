from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.staticfiles.storage import staticfiles_storage
from django_filters.widgets import RangeWidget
from webpack_loader import utils

from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU


class UbereditorWidget(forms.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super().__init__(*args, **kwargs)


class AdminRichTextAreaWidget(UbereditorWidget):
    template_name = 'widgets/ubertextarea.html'


class CKEditorWidget(CKEditorUploadingWidget):
    """
    This class set `contentsCss` config value at runtime before render
    CKEditor widget.

    CKEditor has `contentsCss` setting to pass additional css to ckeditor
    iframe.
    When css served by webpack (in conjunction with staticfiles app) we don't
    know exact path to css file since  bundle name is hashed.
    To avoid this behavior append webpack paths at runtime.
    """
    def _set_config(self):
        super()._set_config()
        css = self.config.get('contentsCss', [])
        for f in utils.get_files('main', 'css'):
            css.append(f["url"])
        css.append('html {margin: 20px;}')
        # TODO: move to settings? how?
        css.append(staticfiles_storage.url('v2/dist/css/main.css'))
        self.config['contentsCss'] = css


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


class DateInputTextWidget(forms.DateInput):
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        format_attrs = {"placeholder": "dd.mm.yyyy"} if format is None else {}
        attrs = {
            "autocomplete": "off",
            "class": "form-control",
            **format_attrs,
            **(attrs or {})
        }
        fmt = format or DATE_FORMAT_RU
        super().__init__(attrs=attrs, format=fmt)


class TimeInputTextWidget(forms.TimeInput):
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        format_attrs = {"placeholder": "hh:mm"} if format is None else {}
        attrs = {
            "autocomplete": "off",
            "class": "form-control",
            **format_attrs,
            **(attrs or {})
        }
        fmt = format or TIME_FORMAT_RU
        super().__init__(attrs=attrs, format=fmt)
