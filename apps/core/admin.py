import datetime

from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse, NoReverseMatch
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from core.timezone import city_aware_to_naive, naive_to_city_aware
from .models import City, Faq, FaqCategory

# Hide applications in the admin
admin.site.unregister(Group)
admin.site.unregister(Site)


def related_spec_to_list(spec):
    list_form = []
    for subspec in spec:
        if isinstance(subspec, tuple):
            parent, children = subspec
            list_form.append(parent)
            list_form.extend("{}__{}".format(parent, x)
                             for x in related_spec_to_list(children))
        else:
            list_form.append(subspec)

    return list_form


def apply_related_spec(qs, related_spec):
    if not related_spec:
        return qs
    if 'select' in related_spec:
        qs = qs.select_related(*related_spec_to_list(related_spec['select']))
    if 'prefetch' in related_spec:
        qs = qs.prefetch_related(*related_spec_to_list(related_spec['prefetch']))
    return qs


class RelatedSpecMixin:
    """
    Extend base queryset with additional values for `select_related` and
    `prefetch_related`.

    Don't forget to add `related_spec` attribute.

    Example:
        ExampleModelAdmin(admin.ModelAdmin):
            related_spec = {'select': [
                                ('assignment',
                                [('course', ['semester', 'meta_course'])]),
                               'student']}

        `related_spec` will be translated to:

            .select_related('assignment',
                            'assignment__course',
                            'assignment__course__semester',
                            'assignment__course__meta_course',
                            'student')
    """
    def get_queryset(self, request):
        qs = super(RelatedSpecMixin, self).get_queryset(request)
        return apply_related_spec(qs, self.related_spec)


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
        raise ValueError(f"Expected model or query, got: {instance_or_qs}")


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


class CityAdmin(TranslationAdmin, admin.ModelAdmin):
    pass


class FaqCategoryAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['name', 'sort']


class FaqAdmin(admin.ModelAdmin):
    list_filter = ['site']
    list_display = ['question', 'sort']


admin.site.register(City, CityAdmin)
admin.site.register(Faq, FaqAdmin)
admin.site.register(FaqCategory, FaqCategoryAdmin)


# TIMEZONE SUPPORT


# FIXME: restrict fields?
class TimezoneAwareModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        """
        Attach model instance to all `AdminSplitDateTime` widgets.
        This allow to get city code inside widget and make datetime
        in a given time zone aware.
        """
        super().__init__(*args, **kwargs)
        for field_name, field_data in self.fields.items():
            if isinstance(field_data, forms.SplitDateTimeField):
                if not isinstance(field_data, TimezoneAwareSplitDateTimeField):
                    raise TypeError("`%s` field must be subclassed from "
                                    "CustomSplitDateTimeField" % field_name)
                widget = field_data.widget
                if isinstance(widget, widgets.AdminSplitDateTime) and \
                        not isinstance(widget, TimezoneAwareAdminSplitDateTimeWidget):
                    raise TypeError("`%s` field widget must be subclassed from "
                                    "BaseCityAwareSplitDateTimeWidget" % field_name)
                else:
                    widget.instance = self.instance

    def save(self, commit=True):
        """
        If city aware field was changed - fix timezone for all datetime fields.
        """
        if self.instance.city_aware_field_name in self.changed_data:
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


class TimezoneAwareAdminSplitDateTimeWidget(widgets.AdminSplitDateTime):
    def decompress(self, value):
        if value:
            value = city_aware_to_naive(value, self.instance)
            return [value.date(), value.time().replace(microsecond=0)]
        return [None, None]


class TimezoneAwareSplitDateTimeField(forms.SplitDateTimeField):
    def compress(self, data_list):
        if data_list:
            # Raise a validation error if time or date is empty
            # (possible if SplitDateTimeField has required=False).
            if data_list[0] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_date'],
                                      code='invalid_date')
            if data_list[1] in self.empty_values:
                raise ValidationError(self.error_messages['invalid_time'],
                                      code='invalid_time')
            result = datetime.datetime.combine(*data_list)
            city_aware = naive_to_city_aware(result, self.widget.instance)
            return city_aware
        return None
