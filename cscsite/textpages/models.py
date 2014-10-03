from __future__ import absolute_import, unicode_literals

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel

from learning.models import LATEX_MARKDOWN_HTML_ENABLED


@python_2_unicode_compatible
class Textpage(TimeStampedModel):
    url_name = models.CharField(
        _("Textpage|url_name"),
        max_length=100,
        editable=False,
        unique=True)
    name = models.CharField(
        _("Textpage|name"),
        editable=False,
        max_length=100)
    text = models.TextField(
        _("News|text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta(object):
        ordering = ["name"]
        verbose_name = _("Textpage|page")
        verbose_name_plural = _("Textpage|pages")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse(self.url_name)


@python_2_unicode_compatible
class CustomTextpage(TimeStampedModel):
    slug = models.SlugField(
        _("News|slug"),
        max_length=70,
        help_text=_("Short dash-separated string "
                    "for human-readable URLs, as in "
                    "compscicenter.ru/pages/<b>some-news</b>/"),
        unique=True)
    name = models.CharField(
        _("Textpage|name"),
        max_length=100)
    text = models.TextField(
        _("News|text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta(object):
        ordering = ["name"]
        verbose_name = _("Textpage|Custom page")
        verbose_name_plural = _("Textpage|Custom pages")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('custom_text_page', args=[self.slug])
