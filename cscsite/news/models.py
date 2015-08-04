from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape

from model_utils.models import TimeStampedModel
from model_utils.fields import SplitField, \
    SPLIT_MARKER, SPLIT_DEFAULT_PARAGRAPHS
from model_utils.managers import QueryManager

from core.models import City


# TODO: "published" should be a date in future
class News(TimeStampedModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               verbose_name=_("News|author"),
                               editable=False,
                               null=True,
                               on_delete=models.SET_NULL)

    title = models.CharField(_("News|title"), max_length=140)

    published = models.BooleanField(_("News|published"),
                                    default=True)

    slug = models.SlugField(_("News|slug"),
                            max_length=70,
                            help_text=_("Short dash-separated string "
                                        "for human-readable URLs, as in "
                                        "test.com/news/<b>some-news</b>/"),
                            unique=True)

    text = SplitField(
        _("News|text"),
        help_text=(_("First {n_par} paragraphs or anything "
                     "before {marker} will serve as excerpt; "
                     "LaTeX+Markdown is enabled")
                   .format(n_par=SPLIT_DEFAULT_PARAGRAPHS,
                           marker=escape(SPLIT_MARKER))))

    city = models.ForeignKey(City, null=True, blank=True, \
                                   default=settings.CITY_CODE)
    site = models.ForeignKey(Site)

    language = models.CharField(max_length=5, db_index=True,
                                choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE)

    class Meta(object):
        ordering = ["-created", "author"]
        verbose_name = _("News|news-singular")
        verbose_name_plural = _("News|news-plural")

    objects = models.Manager()
    public = QueryManager(published=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.author)

    def get_absolute_url(self):
        return reverse('news_detail', args=[str(self.slug)])
