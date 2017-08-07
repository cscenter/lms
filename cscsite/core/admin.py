import datetime

import pytz
import six
import sys

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.urls import reverse, NoReverseMatch
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from sitemetrics.models import Keycode
from modeltranslation.admin import TranslationAdmin

from .models import City, Faq, FaqCategory, University

# Remove groups app from django admin
admin.site.unregister(Group)
# Hide sitemetrics app
admin.site.unregister(Keycode)


def get_admin_url(instance_or_qs):
    """
    A function for extracting admin URL for an object.

    Not all possible URL names are supported, see section
    "Reversing admin URLs" at
    https://docs.djangoproject.com/en/dev/ref/contrib/admin.
    """
    if isinstance(instance_or_qs, QuerySet):
        content_type = ContentType.objects.get_for_model(instance_or_qs.model)
        return reverse(
            "admin:{0.app_label}_{0.model}_changelist".format(content_type))
    elif isinstance(instance_or_qs, Model):
        content_type = ContentType.objects.get_for_model(
            instance_or_qs.__class__)
        return reverse(
            "admin:{0.app_label}_{0.model}_change".format(content_type),
            args=[instance_or_qs.pk])
    else:
        raise ValueError("Expected model or query, got: {0:r}"
                         .format(instance_or_qs))


def urlize(instance, text=None):
    """
    Returns an edit link for a given object.

    :param instance: a model instance to urlize.
    :param text: optional link text, :func:`force_text` is
                 used if no text is given.
    """
    text = text or force_text(instance)
    try:
        link = get_admin_url(instance)
    except (AttributeError, NoReverseMatch):
        return text
    else:
        return '<a href="{0}">{1}</a>'.format(link, text)


def with_link(field_name, text=None):
    text = text or _(field_name.replace("_", " "))

    @meta(text, admin_order_field=field_name, allow_tags=True)
    def inner(self, instance):
        return urlize(getattr(instance, field_name))
    return inner


def meta(text=None, **kwargs):
    """
    Decorator function, setting Django admin metadata.

    :param text: short description of the wrapped method,
                 populated from ``func.__name__`` if omitted.
    """
    def decorator(func):
        func.short_description = text or _(func.__name__)
        for attr in kwargs:
            setattr(func, attr, kwargs[attr])

        return func
    return decorator


class UniversityAdmin(admin.ModelAdmin):
    list_editable = ['sort']
    list_display = ['name', 'city', 'sort']
    list_filter = ['city']


class CityAdmin(TranslationAdmin, admin.ModelAdmin):
    pass


class FaqCategoryAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['name', 'sort']


class FaqAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


admin.site.register(University, UniversityAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Faq, FaqAdmin)
admin.site.register(FaqCategory, FaqCategoryAdmin)


# TIMEZONE SUPPORT

def city_aware_to_naive(value, instance):
    """
    Convert aware datetime to naive in the timezone of the city for display.
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        if not hasattr(instance, "get_city_timezone"):
            raise NotImplementedError("Implement `get_city_timezone` method "
                                      "for %s model" % str(instance.__class__))
        city_timezone = instance.get_city_timezone()
        return timezone.make_naive(value, city_timezone)
    return value


def naive_to_city_aware(value, instance):
    """
    When time zone support is enabled, convert naive datetimes to aware
    datetimes.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        try:
            city_timezone = instance.get_city_timezone()
        except ObjectDoesNotExist:
            # Until city aware field is empty, we can't determine timezone
            city_timezone = pytz.UTC
        try:
            return timezone.make_aware(value, city_timezone)
        except Exception:
            message = _(
                '%(datetime)s couldn\'t be interpreted '
                'in time zone %(city_timezone)s; it '
                'may be ambiguous or it may not exist.'
            )
            params = {'datetime': value, 'current_timezone': city_timezone}
            six.reraise(ValidationError, ValidationError(
                message,
                code='ambiguous_timezone',
                params=params,
            ), sys.exc_info()[2])
    return value


class CityAwareModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """
        Attach model instance to all `AdminSplitDateTime` widgets.
        This allow to get city code inside widget and make datetime city aware.
        """
        super().__init__(*args, **kwargs)
        for field_name, field_data in self.fields.items():
            if isinstance(field_data, forms.SplitDateTimeField):
                if not isinstance(field_data, CityAwareSplitDateTimeField):
                    raise TypeError("`%s` field must be subclassed from "
                                    "CustomSplitDateTimeField" % field_name)
                widget = field_data.widget
                if isinstance(widget, widgets.AdminSplitDateTime) and \
                        not isinstance(widget, CityAwareAdminSplitDateTimeWidget):
                    raise TypeError("`%s` field widget must be subclassed from "
                                    "BaseCityAwareSplitDateTimeWidget" % field_name)
                else:
                    widget.instance = self.instance

    def save(self, commit=True):
        """
        If city aware field was changed - fix timezone for all datetime fields.
        """
        if self.instance.city_aware_field_name in self.changed_data:
            city_timezone = self.instance.get_city_timezone()
            for field_name, field_data in self.fields.items():
                if isinstance(field_data, CityAwareSplitDateTimeField):
                    value = self.cleaned_data[field_name]
                    value = value.replace(tzinfo=None)
                    value = timezone.make_aware(value, city_timezone)
                    self.cleaned_data[field_name] = value
                    setattr(self.instance, field_name, value)
        return super().save(commit)


class CityAwareAdminSplitDateTimeWidget(widgets.AdminSplitDateTime):
    def decompress(self, value):
        if value:
            value = city_aware_to_naive(value, self.instance)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class CityAwareSplitDateTimeField(forms.SplitDateTimeField):
    def compress(self, data_list):
        if data_list:
            # Raise a validation error if time or date is empty
            # (possible if SplitDateTimeField has required=False).
            if data_list[0] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_date'], code='invalid_date')
            if data_list[1] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_time'], code='invalid_time')
            result = datetime.datetime.combine(*data_list)
            city_aware = naive_to_city_aware(result, self.widget.instance)
            return city_aware
        return None
