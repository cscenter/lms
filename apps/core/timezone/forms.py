import datetime

from django import forms
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.utils import timezone

from .utils import aware_to_naive, naive_to_aware


class TimezoneAwareAdminSplitDateTimeWidget(widgets.AdminSplitDateTime):
    def decompress(self, value):
        if value:
            value = aware_to_naive(value, self.instance)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class TimezoneAwareSplitDateTimeField(forms.SplitDateTimeField):
    def compress(self, data_list):
        if data_list:
            # Raise a validation error if time or date is empty
            # (possible with `required=False` field attribute value).
            if data_list[0] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_date'],
                                      code='invalid_date')
            if data_list[1] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_time'],
                                      code='invalid_time')
            result = datetime.datetime.combine(*data_list)
            city_aware = naive_to_aware(result, self.widget.instance)
            return city_aware
        return None


class TimezoneAwareModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """
        Attach model instance to all `AdminSplitDateTime` widgets.
        This allows to get timezone inside widget and makes a datetime
        in a given time zone aware.
        """
        super().__init__(*args, **kwargs)
        for field_name, field_data in self.fields.items():
            if isinstance(field_data, forms.SplitDateTimeField):
                if not isinstance(field_data, TimezoneAwareSplitDateTimeField):
                    raise TypeError(f"`{field_name}` must be subclassed from "
                                    f"{TimezoneAwareSplitDateTimeField}")
                widget = field_data.widget
                if isinstance(widget, widgets.AdminSplitDateTime) and \
                        not isinstance(widget, TimezoneAwareAdminSplitDateTimeWidget):
                    raise TypeError(f"`{field_name}` widget must be subclassed "
                                    f"from {TimezoneAwareAdminSplitDateTimeWidget}")
                else:
                    widget.instance = self.instance

    def save(self, commit=True):
        """
        Update value for all related datetime fields if timezone aware field
        was changed.
        """
        if self.instance.get_tz_aware_field_name() in self.changed_data:
            tz = self.instance.get_timezone()
            for field_name, field_data in self.fields.items():
                if isinstance(field_data, TimezoneAwareSplitDateTimeField):
                    value = self.cleaned_data[field_name]
                    if isinstance(value, datetime.datetime):
                        value = value.replace(tzinfo=None)
                        value = timezone.make_aware(value, tz)
                        self.cleaned_data[field_name] = value
                        setattr(self.instance, field_name, value)
        return super().save(commit)
