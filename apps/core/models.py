from typing import NamedTuple

import pytz
from bitfield import BitField
from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from core.timezone import Timezone, TimezoneAwareModel
from core.urls import reverse
from learning.settings import Branches

BRANCH_CACHE = {}

# FIXME: Move to `checks` module like in django.contrib.admin.checks.check_dependencies
# FIXME: также проверять порядок middleware (до contrib.sites)
REQUIRED_SETTINGS = [
    "SITE_ID",
    "DEFAULT_BRANCH_CODE",
    "DEFAULT_TIMEZONE",
]
for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            f"Please add {attr!r} to the project's settings")


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
        ordering = ["name"]
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self):
        return smart_text(self.name)

    def get_timezone(self):
        if self.code == "online":
            return settings.TIME_ZONES["spb"]
        return settings.TIME_ZONES[self.code]


class BranchNaturalKey(NamedTuple):
    code: str
    site_id: int


class BranchManager(models.Manager):
    use_in_migrations = True

    def _get_branch_by_natural_key(self, key: BranchNaturalKey):
        if key not in BRANCH_CACHE:
            BRANCH_CACHE[key] = self.get(code=key.code, site_id=key.site_id)
        return BRANCH_CACHE[key]

    def _get_branch_by_request(self, request):
        sub_domain = request.get_host().rsplit(request.site.domain, 1)[0][:-1]
        branch_code = sub_domain.lower() or settings.DEFAULT_BRANCH_CODE
        key = BranchNaturalKey(code=branch_code, site_id=request.site.id)
        if key not in BRANCH_CACHE:
            BRANCH_CACHE[key] = self.get(code=key.code, site_id=key.site_id)
        return BRANCH_CACHE[key]

    def get_current(self, request=None, site_id: int = settings.SITE_ID):
        """
        Returns the Branch based on the subdomain of the `request.site`, where
        subdomain is a branch code (e.g. nsk.example.com)
        If request is not provided, returns the Branch based on the
        DEFAULT_BRANCH_CODE value in the project's settings.
        """
        if request:
            return self._get_branch_by_request(request)
        else:
            return self._get_branch_by_natural_key(
                BranchNaturalKey(code=settings.DEFAULT_BRANCH_CODE,
                                 site_id=site_id))

    @staticmethod
    def clear_cache():
        """Clear the ``Branch`` object cache."""
        global BRANCH_CACHE
        BRANCH_CACHE = {}


class Branch(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = TimezoneAwareModel.SELF_AWARE

    code = models.CharField(
        _("Code"),
        max_length=8,
        db_index=True)
    name = models.CharField(_("Branch|Name"), max_length=255)
    order = models.PositiveIntegerField(verbose_name=_('Order'), default=0)
    city = models.ForeignKey(City, verbose_name=_("Branch Location"),
                             blank=True, null=True,
                             on_delete=models.PROTECT)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID,
                             on_delete=models.CASCADE)
    time_zone = models.CharField(verbose_name=_("Timezone"), max_length=63,
                                 choices=tuple(zip(TIMEZONES, TIMEZONES)))
    description = models.TextField(
        _("Description"),
        help_text=_("Branch|Description"),
        blank=True)

    objects = BranchManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code', 'site'),
                                    name='unique_code_per_site'),
        ]
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")

    def __str__(self):
        if self.site_id != settings.SITE_ID:
            return f"{self.name} [{self.site}]"
        else:
            return self.name

    def save(self, *args, **kwargs):
        created = self.pk is None
        super(Branch, self).save(*args, **kwargs)
        Branch.objects.clear_cache()

    def get_timezone(self) -> Timezone:
        return self._timezone

    @cached_property
    def _timezone(self):
        return pytz.timezone(self.time_zone)

    @property
    def abbr(self):
        return Branches.get_choice(self.code).abbr


class Venue(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = TimezoneAwareModel.SELF_AWARE

    INTERVIEW = 'interview'
    LECTURE = 'lecture'
    UNSPECIFIED = 0  # BitField uses BigIntegerField internal

    city = models.ForeignKey(City, null=True, blank=True,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.PROTECT)
    name = models.CharField(_("Venue|Name"), max_length=140)
    address = models.CharField(
        _("Venue|Address"),
        help_text=(_("Should be resolvable by Google Maps")),
        max_length=500,
        blank=True)
    description = models.TextField(
        _("Description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    directions = models.TextField(
        _("Directions"),
        blank=True,
        null=True)
    flags = BitField(
        verbose_name=_("Flags"),
        flags=(
            (LECTURE, _('Class')),
            (INTERVIEW, _('Interview')),
        ),
        default=(LECTURE,),
        help_text=(_("Set purpose of this place")))
    is_preferred = models.BooleanField(
        _("Preferred"),
        help_text=(_("Will be displayed on top of the venue list")),
        default=False)

    class Meta:
        ordering = ["-is_preferred", "name"]
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def get_timezone(self):
        return settings.TIME_ZONES[self.city_id]

    def __str__(self):
        return "{0}".format(smart_text(self.name))

    def get_absolute_url(self):
        return reverse('venue_detail', args=[self.pk])
