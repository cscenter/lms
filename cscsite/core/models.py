# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

LATEX_MARKDOWN_HTML_ENABLED = _(
    "How to style text read <a href=\"/commenting-the-right-way/\" "
    "target=\"_blank\">here</a>. Partially HTML is enabled too.")
LATEX_MARKDOWN_ENABLED = _(
    "How to style text read <a href=\"/commenting-the-right-way/\" "
    "target=\"_blank\">here</a>."
)


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
    # Note: Now `CurrentCityMiddleware` hardcoded to cities from Russia.
    code = models.CharField(
        _("Code"),
        max_length=6,
        help_text=_("UN/LOCODE notification preferable <a href='http://www.unece.org/cefact/locode/service/location' target='_blank'>Hint</a>"),
        primary_key=True)
    name = models.CharField(_("City name"), max_length=255)

    class Meta:
        db_table = 'cities'
        ordering = ["name"]
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self):
        return smart_text(self.name)

    @property
    def iata(self):
        """UN/LOCODE consists of country code + IATA"""
        iata = self.code.split(sep=" ")[-1]
        return iata.lower()


@python_2_unicode_compatible
class FaqCategory(models.Model):
    name = models.CharField(_("Category name"), max_length=255)
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"), default=settings.CENTER_SITE_ID)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("FAQ category")
        verbose_name_plural = _("FAQ categories")

    def __str__(self):
        return smart_text(self.name)


@python_2_unicode_compatible
class Faq(models.Model):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"), default=settings.CENTER_SITE_ID)
    categories = models.ManyToManyField(
        FaqCategory,
        verbose_name=_("Categories"),
        related_name='categories',
        blank=True)

    class Meta:
        db_table = 'faq'
        ordering = ["sort"]
        verbose_name = _("FAQ")
        verbose_name_plural = _("Questions&Answers")

    def __str__(self):
        return smart_text(self.question)
