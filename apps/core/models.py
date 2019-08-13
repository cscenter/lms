# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import models
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _

from core.mixins import TimezoneAwareModel
from learning.settings import Branches

LATEX_MARKDOWN_HTML_ENABLED = _(
    "How to style text read <a href=\"/commenting-the-right-way/\" "
    "target=\"_blank\">here</a>. Partially HTML is enabled too.")
LATEX_MARKDOWN_ENABLED = _(
    "How to style text read <a href=\"/commenting-the-right-way/\" "
    "target=\"_blank\">here</a>."
)


class City(models.Model):
    code = models.CharField(
        _("Code"),
        max_length=6,
        primary_key=True)
    name = models.CharField(_("City name"), max_length=255)
    abbr = models.CharField(_("Abbreviation"), max_length=20)

    class Meta:
        db_table = 'cities'
        ordering = ["name"]
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self):
        return smart_text(self.name)

    def get_timezone(self):
        if self.code == "online":
            return settings.TIME_ZONES["spb"]
        return settings.TIME_ZONES[self.code]


class Branch(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = TimezoneAwareModel.SELF_AWARE

    code = models.CharField(
        _("Code"),
        choices=Branches.choices,
        max_length=8,
        unique=True)
    name = models.CharField(_("Branch|Name"), max_length=255)
    is_remote = models.BooleanField(_("Distance Branch"), default=False)
    description = models.TextField(
        _("Description"),
        help_text=_("Branch|Description"),
        blank=True)

    class Meta:
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")

    def __str__(self):
        return self.name

    @property
    def order(self):
        return Branches.get_choice(self.code).order

    def get_timezone(self):
        return Branches.get_choice(self.code).timezone

    @property
    def abbr(self):
        return Branches.get_choice(self.code).abbr