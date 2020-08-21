# -*- coding: utf-8 -*-

from django.db import models
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _


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
        return smart_str(self.question)
