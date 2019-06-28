from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase, TagBase

from core.urls import reverse
from core.utils import ru_en_mapping

ACTIONS_DEFAULT = """\
<a class="btn _big _primary _m-wide" href="">Зарегистрироваться</a>
"""


class AnnouncementTag(TagBase):
    modifier = models.CharField(
        verbose_name=_("Modifier"),
        max_length=20,
        help_text=_("This class could affect the tag view"),
        blank=True, null=True)

    class Meta:
        verbose_name = _("Announcement Tag")
        verbose_name_plural = _("Announcement Tags")

    def slugify(self, tag, i=None):
        """Transliterates cyrillic symbols before slugify"""
        tag = tag.translate(ru_en_mapping)
        return super().slugify(tag, i)


class TaggedAnnouncement(TaggedItemBase):
    content_object = models.ForeignKey('Announcement',
                                       on_delete=models.CASCADE,)
    tag = models.ForeignKey(AnnouncementTag,
                            related_name="%(app_label)s_%(class)s_items",
                            on_delete=models.CASCADE)


class AnnouncementCurrentManager(models.Manager):
    """
    Announcement manager for dealing with current announcements.
    """

    def get_queryset(self):
        now_utc = timezone.now()
        return super().get_queryset().filter(
            publish_start_at__lte=now_utc,
            publish_end_at__gte=now_utc
        )


class Announcement(TimeStampedModel):
    name = models.CharField(_("Title"), max_length=255)
    publish_start_at = models.DateTimeField(
        _("Publish Start at"),
        default=timezone.now)
    publish_end_at = models.DateTimeField(_("Publish End at"))
    tags = TaggableManager(through=TaggedAnnouncement, blank=True)
    short_description = models.TextField(_("Short Description"))
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Don't forget to add &lt;h3&gt;Title&lt;/h3&gt; on the first line"),
        blank=True)
    thumbnail = models.ImageField(
        _("Photo"),
        upload_to="announcements/",
        blank=True,
        null=True,
        help_text=_("Recommended dimensions 600x400"))
    event_date_at = models.DateTimeField(
        _("Event Date"),
        blank=True,
        null=True)
    event_place = models.CharField(_("Event Place"), max_length=255, blank=True)
    event_actions = models.TextField(
        _("Actions"),
        blank=True,
        default=ACTIONS_DEFAULT.strip())

    objects = models.Manager()
    current = AnnouncementCurrentManager()

    class Meta:
        verbose_name = _("Announcement")
        verbose_name_plural = _("Announcements")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("announcements:announcement_detail",
                       kwargs={"pk": self.pk})
