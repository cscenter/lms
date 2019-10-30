from crispy_forms.utils import render_crispy_form
from jinja2 import contextfunction

from core.utils import render_markdown_and_cache


def markdown(value, fragment_name, expires_in=0, *vary_on):
    return render_markdown_and_cache(value, fragment_name, expires_in, *vary_on)


@contextfunction
def crispy(context, form):
    return render_crispy_form(form, context=context)
