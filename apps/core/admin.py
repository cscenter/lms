from typing import Sequence

from bitfield import BitField
from bitfield.forms import BitFieldCheckboxSelectMultiple
from modeltranslation.admin import TranslationAdmin
from taggit.models import Tag

from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db.models import Model
from django.db.models.query import QuerySet
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from core.models import Location, University
from core.widgets import AdminRichTextAreaWidget

from .models import Branch, City

# Hide applications in the admin
admin.site.unregister(Group)
admin.site.unregister(Site)

# Hide taggit application
admin.site.unregister(Tag)


class BaseModelAdmin(admin.ModelAdmin):
    list_select_related: Sequence[str] = []
    list_prefetch_related: Sequence[str] = []

    def get_prefetch_related(self):
        return self.list_prefetch_related

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        list_prefetch_related = self.get_prefetch_related()
        if list_prefetch_related:
            queryset = queryset.prefetch_related(*list_prefetch_related)
        return queryset


def get_admin_url(obj):
    """
    A function for extracting admin URL for an object.

    Not all possible URL names are supported, see section
    "Reversing admin URLs" at
    https://docs.djangoproject.com/en/dev/ref/contrib/admin.
    """
    if isinstance(obj, Model):
        content_type = ContentType.objects.get_for_model(obj.__class__)
        return reverse(
            "admin:{0.app_label}_{0.model}_change".format(content_type),
            args=[obj.pk])
    else:
        raise ValueError(f"Expected model, got: {obj}")


def urlize(instance, text=None):
    """
    Returns an edit link for a given object.

    :param instance: a model instance to urlize.
    :param text: optional link text, :func:`force_str` is
                 used if no text is given.
    """
    text = text or force_str(instance)
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


# Models

@admin.register(City)
class CityAdmin(TranslationAdmin, admin.ModelAdmin):
    pass


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'site', 'order', 'city', 'active')
    list_filter = ('site',)


class LocationAdminForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = '__all__'
        widgets = {
            'description': AdminRichTextAreaWidget(),
        }


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    form = LocationAdminForm
    formfield_overrides = {
        BitField: {'widget': BitFieldCheckboxSelectMultiple},
    }
    list_display = ('name', 'city')
    list_filter = ('city',)
    list_select_related = ("city",)


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'city')
    ordering = ('name',)
