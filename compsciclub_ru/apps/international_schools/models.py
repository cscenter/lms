from model_utils.models import TimeStampedModel

from django.db import models
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _


class InternationalSchool(TimeStampedModel):
    name = models.CharField(_("InternationalSchool|name"), max_length=255)
    link = models.URLField(
        _("InternationalSchool|Link"))
    place = models.CharField(_("InternationalSchool|place"), max_length=255)
    deadline = models.DateField(_("InternationalSchool|Deadline"))
    starts_at = models.DateField(_("InternationalSchool|Start"))
    ends_at = models.DateField(_("InternationalSchool|End"), blank=True,
                               null=True)
    has_grants = models.BooleanField(
        _("InternationalSchool|Grants"),
        default=False)

    class Meta:
        db_table = 'international_schools'
        ordering = ["name"]
        verbose_name = _("International School")
        verbose_name_plural = _("International Schools")

    def __str__(self):
        return smart_str(self.name)
