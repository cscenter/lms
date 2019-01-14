# -*- coding: utf-8 -*-
import types

from django import template
from django.conf import settings
from django.forms import forms
from django.template import Context, TemplateSyntaxError
from django.template.loader import get_template
from django.utils.lru_cache import lru_cache


register = template.Library()


#@lru_cache()
def get_form_template(template_pack=None):
    if not template_pack:
        return get_template('surveys/forms/form.html')
    return get_template('surveys/forms/%s/form.html' % template_pack)


def get_widget_context(self, name, value, attrs):
    # Call the original widget.get_context method
    context = self.__class__.get_context(self, name, value, attrs)
    context['field'] = self.bound_field.field
    context['errors'] = self.bound_field.errors
    return context


@register.filter(name='as_survey')
def render_form(form, template_pack=None):
    """
    Renders an entire form.

    Each field representation is a compound widget consists of label,
    input, help block, etc, but Django's field widget system allows to
    customize only field input.
    It means we can't use field layout like this one:
        <div class="wrapper input">
            <label for="">Label</label>
            <input type="text" ...>  # Django's widget template
        </div>

    At least we haven't access to the field properties like label, help_text.
    This filter injects field instance to the widget what allows overcome this.

    Usage:
        {% load form_utils %}

        <form action="" method="post">
            {% csrf_token %}
            {{ myform|as_survey }}
        </form>

    or, if you want to explicitly set the template pack::

        {{ myform|as_survey:"csc" }}
    """

    if not isinstance(form, forms.BaseForm) and settings.DEBUG:
        msg = '|colorize form must be inherited from BaseForm'
        raise TemplateSyntaxError(msg)

    template = get_form_template(template_pack)
    for bound_field in form:
        widget = bound_field.field.widget
        widget.bound_field = bound_field
        widget.get_context = types.MethodType(get_widget_context, widget)
    c = Context({
        'form': form,
    }).flatten()

    return template.render(c)
