from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel


class InternshipCategory(models.Model):
    name = models.CharField(_("Category name"), max_length=255)
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID,
                             on_delete=models.CASCADE)

    class Meta:
        db_table = "internships_categories"
        ordering = ["sort"]
        verbose_name = _("Internship category")
        verbose_name_plural = _("Internship categories")

    def __str__(self):
        return smart_text(self.name)


class Internship(TimeStampedModel):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    category = models.ForeignKey(InternshipCategory,
                                 verbose_name=_("Internship category"),
                                 null=True,
                                 blank=True,
                                 on_delete=models.SET_NULL)

    class Meta:
        db_table = "internships"
        ordering = ["sort"]
        verbose_name = _("Internship")
        verbose_name_plural = _("Internships")

    def __str__(self):
        return smart_text(self.question)
