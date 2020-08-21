import datetime

import pytz
from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.widgets import DateInputTextWidget, TimeInputTextWidget
from .models import TimezoneAwareDateTimeField, TimezoneAwareModel


def aware_to_naive(value, instance: TimezoneAwareModel):
    """
    Make an aware datetime.datetime naive in a time zone of the given instance
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        instance_timezone = instance.get_timezone()
        return timezone.make_naive(value, instance_timezone)
    return value


def naive_to_aware(value, instance: TimezoneAwareModel):
    """
    Make a naive datetime.datetime in a given instance time zone aware.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        try:
            instance_tz = instance.get_timezone()
        except ObjectDoesNotExist:
            # Can't retrieve timezone until timezone aware field is empty
            instance_tz = pytz.UTC
        try:
            return timezone.make_aware(value, instance_tz)
        except Exception as exc:
            msg = _(
                '%(datetime)s couldn\'t be interpreted in time zone '
                '%(instance_tz)s; it may be ambiguous or it may not exist.'
            )
            params = {'datetime': value, 'instance_tz': instance_tz}
            raise ValidationError(
                msg,
                code='ambiguous_timezone',
                params=params) from exc
    return value


class TimezoneAwareSplitDateTimeWidget(forms.SplitDateTimeWidget):
    template_name = "widgets/timezone_aware_split_datetime.html"  # bootstrap 3

    def __init__(self, attrs=None):
        widgets = [DateInputTextWidget, TimeInputTextWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def decompress(self, value):
        if value:
            value = aware_to_naive(value, self.instance)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class TimezoneAwareAdminSplitDateTimeWidget(widgets.AdminSplitDateTime):
    def decompress(self, value):
        # noinspection PyCallByClass
        return TimezoneAwareSplitDateTimeWidget.decompress(self, value)


class TimezoneAwareFormField(forms.Field):
    pass


class TimezoneAwareSplitDateTimeField(TimezoneAwareFormField,
                                      forms.SplitDateTimeField):
    widget = TimezoneAwareSplitDateTimeWidget
    # TODO: customize hidden widget?

    def compress(self, data_list):
        if data_list:
            # Raise validation error if time or date is empty
            # (possible with `required=False` field attribute value).
            if data_list[0] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_date'],
                                      code='invalid_date')
            if data_list[1] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_time'],
                                      code='invalid_time')
            dt_naive = datetime.datetime.combine(*data_list)
            return naive_to_aware(dt_naive, self.widget.instance)
        return None


class TimezoneAwareModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """
        Links a model instance to a field widget if the field is aware of
        timezone.
        """
        super().__init__(*args, **kwargs)
        if not isinstance(self.instance, TimezoneAwareModel):
            raise TypeError(f"{TimezoneAwareModelForm.__class__}.instance "
                            f"must be subclassed from {TimezoneAwareModel}")
        for field_name, form_field in self.fields.items():
            if isinstance(form_field, TimezoneAwareFormField):
                form_field.widget.instance = self.instance

    def save(self, commit=True):
        """
        Update value for all related datetime fields if timezone aware field
        was changed.
        """
        if self.instance.get_tz_aware_field_name() in self.changed_data:
            tz = self.instance.get_timezone()
            for field_name, form_field in self.fields.items():
                if isinstance(form_field, TimezoneAwareFormField):
                    value = self.cleaned_data[field_name]
                    if isinstance(value, datetime.datetime):
                        value = value.replace(tzinfo=None)
                        value = timezone.make_aware(value, tz)
                        self.cleaned_data[field_name] = value
                        setattr(self.instance, field_name, value)
        return super().save(commit)


class TimezoneAwareAdminForm(TimezoneAwareModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, form_field in self.fields.items():
            model_field = self._meta.model._meta.get_field(field_name)
            if isinstance(model_field, TimezoneAwareDateTimeField):
                if not isinstance(form_field, TimezoneAwareSplitDateTimeField):
                    raise TypeError(f"`{field_name}` must be subclassed from "
                                    f"{TimezoneAwareSplitDateTimeField}")
                widget = form_field.widget
                if not isinstance(widget, TimezoneAwareAdminSplitDateTimeWidget):
                    raise TypeError(f"`{field_name}` widget must be subclassed "
                                    f"from {TimezoneAwareAdminSplitDateTimeWidget}")
