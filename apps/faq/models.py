from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_("Name"), max_length=255)
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID, on_delete=models.PROTECT)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return smart_text(self.name)


class Question(models.Model):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID, on_delete=models.PROTECT)
    categories = models.ManyToManyField(
        Category,
        verbose_name=_("Categories"),
        related_name='categories',
        blank=True)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self):
        return smart_text(self.question)
