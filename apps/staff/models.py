# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class Hint(models.Model):
    """Contains hints for curators"""
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Hint")
        verbose_name_plural = _("Warehouse")

    def __str__(self):
        return smart_text(self.question)
