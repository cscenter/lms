# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.db import models
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


LATEX_MARKDOWN_HTML_ENABLED = _(
    "LaTeX+"
    "<a href=\"http://en.wikipedia.org/wiki/Markdown\">Markdown</a>+"
    "HTML is enabled")
LATEX_MARKDOWN_ENABLED = _(
    "LaTeX+"
    "<a href=\"http://en.wikipedia.org/wiki/Markdown\">Markdown</a>"
    " is enabled")


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


@python_2_unicode_compatible
class City(models.Model):
    code = models.CharField(
        _("Code"),
        max_length=6,
        help_text=_("UN/LOCODE notification preferable"),
        primary_key=True)
    name = models.CharField(_("City name"), max_length=255)

    class Meta:
        db_table = 'cities'
        ordering = ["name"]
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self):
        return smart_text(self.name)
