# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

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
