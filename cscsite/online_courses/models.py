from typing import NamedTuple

from django.db import models
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel, TimeFramedModel
from sorl.thumbnail import ImageField

from core.models import LATEX_MARKDOWN_HTML_ENABLED


class OnlineCourseTuple(NamedTuple):
    name: str
    link: str
    avatar_url: str
    tag: str


class OnlineCourse(TimeStampedModel, TimeFramedModel):
    name = models.CharField(_("Course|name"), max_length=255)
    teachers = models.TextField(
        _("Online Course|teachers"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    description = models.TextField(
        _("Online Course|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    link = models.URLField(
        _("Online Course|Link"))
    photo = ImageField(
        _("Online Course|photo"),
        upload_to="online_courses/",
        blank=True)
    is_au_collaboration = models.BooleanField(
        _("Collaboration with AY"),
        default=False)
    is_self_paced = models.BooleanField(
        _("Without deadlines"),
        default=False)

    class Meta:
        db_table = 'online_courses'
        ordering = ["name"]
        verbose_name = _("Online course")
        verbose_name_plural = _("Online courses")

    def __str__(self):
        return smart_text(self.name)

    def is_ongoing(self):
        return self.start and self.start <= timezone.now()

    @property
    def avatar_url(self):
        if self.photo:
            return self.photo.url
        return None
