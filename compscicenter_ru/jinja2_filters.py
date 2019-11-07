from crispy_forms.utils import render_crispy_form
from jinja2 import contextfunction

from core.utils import render_markdown_and_cache, get_youtube_video_id


def markdown(value, fragment_name, expires_in=0, *vary_on):
    return render_markdown_and_cache(value, fragment_name, expires_in, *vary_on)


@contextfunction
def crispy(context, form):
    return render_crispy_form(form, context=context)


def pluralize(number, singular, genitive_singular, genitive_plural):
    """Plurals with numbers"""
    endings = [singular, genitive_singular, genitive_plural]
    if number % 100 in (11, 12, 13, 14):
        return endings[2]
    if number % 10 == 1:
        return endings[0]
    if number % 10 in (2, 3, 4):
        return endings[1]
    else:
        return endings[2]


def youtube_video_id(url):
    return get_youtube_video_id(url)
