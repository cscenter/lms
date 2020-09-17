from base64 import b64encode, urlsafe_b64encode
from typing import NamedTuple, Dict, Union, NewType, List

import pytz
from bitfield import BitField
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models, router
from django.utils.encoding import smart_str, force_bytes, force_str
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

from core.timezone import Timezone, TimezoneAwareModel
from core.urls import reverse


class BranchNaturalKey(NamedTuple):
    code: str
    site_id: int


SiteId = NewType('SiteId', int)
BranchId = NewType('BranchId', int)

# TODO: Move to shared cache since it's hard to clear in all processes
BRANCH_CACHE: Dict[Union[BranchId, BranchNaturalKey], "Branch"] = {}
BRANCH_SITE_CACHE: Dict[SiteId, List[BranchId]] = {}


LATEX_MARKDOWN_HTML_ENABLED = _(
    "How to style text read <a href=\"/commenting-the-right-way/\" "
    "target=\"_blank\">here</a>. Partially HTML is enabled too.")
LATEX_MARKDOWN_ENABLED = _(
    "How to style text read <a href=\"/commenting-the-right-way/\" "
    "target=\"_blank\">here</a>."
)

TIMEZONES = (
    'Europe/Kiev',
    'Europe/Moscow',
    'Europe/Minsk',
    'Asia/Yekaterinburg',
    'Asia/Novosibirsk',
)


class ConfigurationModel(TimeStampedModel):
    """Abstract base class for model-based configuration"""

    enabled = models.BooleanField(default=False, verbose_name=_("Enabled"))
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_("Changed by"))

    class Meta:
        abstract = True


class SiteConfiguration(ConfigurationModel):
    site = models.OneToOneField(
        Site,
        verbose_name="Site",
        on_delete=models.CASCADE,
        related_name='site_configuration')
    default_from_email = models.CharField(
        "Default Email Address",
        max_length=255)
    email_backend = models.CharField(
        "Email Backend",
        help_text="Python import path of the backend to use for sending emails",
        max_length=255)
    email_host = models.CharField(
        "Email Host",
        help_text="The host to use for sending email",
        max_length=255)
    email_host_password = models.CharField(
        "Email Host Password",
        help_text="Password to use for the SMTP server defined in EMAIL_HOST. "
                  "Should be encrypted with a symmetric key stored in a "
                  "settings.SECRET_KEY",
        max_length=255)
    email_host_user = models.CharField(
        "Email Host User",
        help_text="Username to use for the SMTP server defined in EMAIL_HOST",
        max_length=255)
    email_port = models.PositiveSmallIntegerField(
        "Email Port",
        help_text="Port to use for the SMTP server defined in EMAIL_HOST.")
    email_use_tls = models.BooleanField(
        "Use TLS",
        help_text="Whether to use an explicit TLS (secure) connection when "
                  "talking to the SMTP server")
    email_use_ssl = models.BooleanField(
        "Use SSL",
        help_text="Whether to use an implicit TLS (secure) connection when "
                  "talking to the SMTP server.")
    lms_subdomain = models.CharField(
        "LMS Subdomain",
        max_length=10,
        blank=True,
        null=True)
    default_branch_code = models.CharField(
        "Branch code",
        max_length=10)

    class Meta:
        verbose_name = "Site Configuration"
        db_table = "site_configurations"

    @classmethod
    def _get_fernet_key(cls):
        """Fernet key must be 32 url-safe base64-encoded bytes"""
        key = force_bytes(settings.DB_SECRET_KEY)[:32]
        return urlsafe_b64encode(key.ljust(32, b"="))

    @classmethod
    def encrypt(cls, value) -> str:
        f = Fernet(cls._get_fernet_key())
        return force_str(f.encrypt(force_bytes(value)))

    @classmethod
    def decrypt(cls, value) -> str:
        f = Fernet(cls._get_fernet_key())
        return force_str(f.decrypt(force_bytes(value)))


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TrashManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=False)


class SoftDeletionModel(models.Model):
    """Abstract base class for model soft deletion"""
    deleted_at = models.DateTimeField(db_index=True, blank=True, null=True)

    objects = LiveManager()
    trash = TrashManager()
    base = models.Manager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return bool(self.deleted_at)

    def delete(self, using=None, permanent=False):
        from core.services import SoftDeleteService
        if permanent:
            super().delete(using=using, keep_parents=False)
        else:
            using = using or router.db_for_write(self.__class__, instance=self)
            assert self.pk is not None, (
                "%s object can't be deleted because its %s attribute is set to None." %
                (self._meta.object_name, self._meta.pk.attname)
            )
            SoftDeleteService(using).delete([self])

    def restore(self, using=None):
        from core.services import SoftDeleteService
        if self.deleted_at:
            using = using or router.db_for_write(self.__class__, instance=self)
            SoftDeleteService(using).restore([self])


class City(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = TimezoneAwareModel.SELF_AWARE

    code = models.CharField(
        _("Code"),
        max_length=6,
        primary_key=True)
    name = models.CharField(_("City name"), max_length=255)
    abbr = models.CharField(_("Abbreviation"), max_length=20)
    time_zone = models.CharField(verbose_name=_("Timezone"), max_length=63,
                                 choices=tuple(zip(TIMEZONES, TIMEZONES)))

    class Meta:
        ordering = ["name"]
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self):
        return smart_str(self.name)

    def get_timezone(self) -> Timezone:
        return self._timezone

    @cached_property
    def _timezone(self):
        return pytz.timezone(self.time_zone)


class BranchManager(models.Manager):
    use_in_migrations = False

    def get_by_pk(self, branch_id: int):
        pk = BranchId(branch_id)
        if pk not in BRANCH_CACHE:
            BRANCH_CACHE[pk] = self.get(pk=pk)
        return BRANCH_CACHE[pk]

    def get_by_natural_key(self, code, site_id):
        key = BranchNaturalKey(code=code, site_id=site_id)
        if key not in BRANCH_CACHE:
            BRANCH_CACHE[key] = self.get(code=key.code, site_id=key.site_id)
        return BRANCH_CACHE[key]

    def for_site(self, site_id: int, all=False) -> List["Branch"]:
        """
        Returns active branches for concrete site. Pass in `all=True` to
        include inactive branches.
        """
        cache_key = SiteId(site_id)
        if cache_key not in BRANCH_SITE_CACHE:
            branches = list(self.filter(site_id=site_id).order_by('order'))
            if not branches:
                return []
            for b in branches:
                key = BranchId(b.pk)
                BRANCH_CACHE[key] = b
            BRANCH_SITE_CACHE[cache_key] = [BranchId(b.pk) for b in branches]
        branches = [BRANCH_CACHE[pk] for pk in BRANCH_SITE_CACHE[cache_key]]
        if all:
            return branches
        return [b for b in branches if b.active]

    def get_current(self, request, site_id: int = settings.SITE_ID):
        """
        Returns the Branch based on the subdomain of the `request.site`, where
        subdomain is a branch code (e.g. nsk.example.com)
        If request is not provided, returns the Branch based on the
        DEFAULT_BRANCH_CODE value in the project's settings.
        """
        sub_domain = request.get_host().rsplit(request.site.domain, 1)[0][:-1]
        branch_code = sub_domain.lower() or settings.DEFAULT_BRANCH_CODE
        if branch_code == "www":
            branch_code = settings.DEFAULT_BRANCH_CODE
        key = BranchNaturalKey(code=branch_code, site_id=request.site.id)
        if key not in BRANCH_CACHE:
            BRANCH_CACHE[key] = self.get(code=key.code, site_id=key.site_id)
        return BRANCH_CACHE[key]

    @staticmethod
    def clear_cache():
        """Clear the ``Branch`` object caches."""
        global BRANCH_CACHE, BRANCH_SITE_CACHE
        BRANCH_CACHE = {}
        BRANCH_SITE_CACHE = {}


class Branch(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = TimezoneAwareModel.SELF_AWARE

    code = models.CharField(
        _("Code"),
        max_length=8,
        db_index=True)
    name = models.CharField(_("Branch|Name"), max_length=255)
    established = models.PositiveIntegerField(_('Established'))
    active = models.BooleanField(
        verbose_name=_("Active"),
        default=True)
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

    default_manager = models.Manager()
    objects = BranchManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code', 'site'),
                                    name='unique_code_per_site'),
        ]
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")

    def __str__(self):
        return f"{self.name} [{self.site}]"

    def save(self, *args, **kwargs):
        created = self.pk is None
        super(Branch, self).save(*args, **kwargs)
        Branch.objects.clear_cache()

    def natural_key(self):
        return BranchNaturalKey(self.code, self.site_id)

    def get_timezone(self) -> Timezone:
        return self._timezone

    @cached_property
    def _timezone(self):
        return pytz.timezone(self.time_zone)


class Location(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = 'city'

    INTERVIEW = 'interview'
    LECTURE = 'lecture'
    UNSPECIFIED = 0  # BitField uses BigIntegerField internal

    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.PROTECT)
    name = models.CharField(_("Location|Name"), max_length=140)
    address = models.CharField(
        _("Address"),
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

    class Meta:
        ordering = ("name",)
        verbose_name = _("Location|Name")
        verbose_name_plural = _("Locations")

    def __str__(self):
        return "{0}".format(smart_str(self.name))

    def get_absolute_url(self):
        return reverse('courses:venue_detail', args=[self.pk])
