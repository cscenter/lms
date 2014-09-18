from __future__ import absolute_import, unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from .forms import Ubereditor


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


class UbereditorMixin(object):
    change_form_template = "admin/ubereditor_change_form.html"

    def __init__(self, *args, **kwargs):
        self.formfield_overrides.update(
            {models.TextField: {'widget': Ubereditor}})

        super(UbereditorMixin, self).__init__(*args, **kwargs)


class WiderLabelsMixin(object):
    class Media:
        css = {'all': ["css/admin-wider-fields.css"]}
