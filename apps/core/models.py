# -*- coding: utf-8 -*-
import datetime

import pytz
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
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

TIMEZONES = (
    'Europe/Moscow',
    'Asia/Novosibirsk',
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
        max_length=8,
        db_index=True)
    name = models.CharField(_("Branch|Name"), max_length=255)
    order = models.PositiveIntegerField(verbose_name=_('Order'), default=0)
    is_remote = models.BooleanField(_("Distance Branch"), default=False)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID,
                             on_delete=models.CASCADE)
    time_zone = models.CharField(verbose_name=_("Timezone"), max_length=63,
                                 choices=tuple(zip(TIMEZONES, TIMEZONES)))
    description = models.TextField(
        _("Description"),
        help_text=_("Branch|Description"),
        blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code', 'site'),
                                    name='unique_code_per_site'),
        ]
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")

    def __str__(self):
        return f"{self.name} [{self.site}]"

    def get_timezone(self) -> datetime.tzinfo:
        return self._timezone

    @cached_property
    def _timezone(self):
        return pytz.timezone(self.time_zone)

    @property
    def abbr(self):
        return Branches.get_choice(self.code).abbr