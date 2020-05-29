from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from core.utils import ru_en_mapping
from info_blocks.managers import InfoBlockDefaultManager


class CurrentInfoBlockTags:
    """
    These tags are used to display relevant items in current views for useful, honor code and internships.
    Need to be kept in sync with actual DB values, will be removed in favor of tabs in the new design.
    """
    USEFUL = _("Infoblock|Useful")
    HONOR_CODE = _("Infoblock|Honor Code")
    INTERNSHIP = _("Infoblock|Internships")


class InfoBlockTag(TagBase):
    class Meta:
        db_table = "infoblock_tags"
        verbose_name = _("Infoblock Tag")
        verbose_name_plural = _("Infoblock Tags")

    def __str__(self):
        return smart_text(self.name)

    def slugify(self, tag, i=None):
        """Transliterates cyrillic symbols before slugify"""
        tag = tag.translate(ru_en_mapping)
        return super().slugify(tag, i)


class TaggedInfoBlock(TaggedItemBase):
    content_object = models.ForeignKey('InfoBlock',
                                       on_delete=models.CASCADE)
    tag = models.ForeignKey(
        InfoBlockTag,
        on_delete=models.CASCADE
    )


class InfoBlock(TimeStampedModel):
    title = models.CharField(_("Title"), max_length=255)
    content = models.TextField(_("Content"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID,
                             on_delete=models.CASCADE,
                             related_name='infoblock_set')
    tags = TaggableManager(through=TaggedInfoBlock)

    objects = InfoBlockDefaultManager()

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Infoblock")
        verbose_name_plural = _("Infoblocks")

    def __str__(self):
        if not self.title:
            return smart_text(self.content)
        return smart_text(self.title)
