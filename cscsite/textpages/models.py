from __future__ import unicode_literals

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel


class Textpage(TimeStampedModel):
    url_name = models.CharField(_("Textpage|url_name"),
                                max_length=100,
                                editable=False,
                                unique=True)
    name = models.CharField(_("Textpage|name"),
                            editable=False,
                            max_length=100)
    text = models.TextField(_("News|text"),
                            help_text=_("LaTeX+Markdown is enabled"))

    class Meta(object):
        ordering = ["url_name"]
        verbose_name = _("Textpage|page")
        verbose_name_plural = _("Textpage|pages")

    def __unicode__(self):
        return unicode(self.name)

    def get_absolute_url(self):
        return reverse(self.url_name)
