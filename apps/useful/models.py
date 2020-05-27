from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager
from taggit.models import TagBase, GenericTaggedItemBase

from useful.managers import UsefulDefaultManager


class CurrentUsefulTags:
    """
    These tags are used to display relevant items in current views for useful, honor code and internships.
    Need to be kept in sync with actual DB values, will be removed in favor of tabs in the new design.
    """
    USEFUL = "Полезное"
    HONOR_CODE = "Кодекс чести"
    INTERNSHIP = "Проекты организаторов"


class UsefulTag(TagBase):
    class Meta:
        db_table = "useful_tags"
        verbose_name = _("Useful Tag")
        verbose_name_plural = _("Useful Tags")

    def __str__(self):
        return smart_text(self.name)


class TaggedUsefulItem(GenericTaggedItemBase):
    tag = models.ForeignKey(
        UsefulTag,
        on_delete=models.CASCADE
    )


class Useful(TimeStampedModel):
    title = models.CharField(_("Title"), max_length=255)
    content = models.TextField(_("Content"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID,
                             on_delete=models.CASCADE,
                             related_name='useful_set')
    tags = TaggableManager(through=TaggedUsefulItem)

    objects = UsefulDefaultManager()

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Useful")
        verbose_name_plural = _("Useful")

    def __str__(self):
        if not self.title:
            return smart_text(self.content)
        return smart_text(self.title)
