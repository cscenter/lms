from django.db import models
from django.core.urlresolvers import reverse
from model_utils.models import TimeStampedModel

class News(TimeStampedModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=30,
                            help_text="short underscore-separated string " \
                                "for human-readable URLs, as in " \
                                "test.com/news/<b>some_news</b>/",
                            unique=True)
    short_text = models.TextField(max_length=140,
                                  help_text="140 symbols max")
    full_text = models.TextField(max_length=(1024 * 4),
                                  help_text="4kb max")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        # return u"%s (%s)" % (self.title, self.author)
        return u"%s" % (self.slug)

    def get_absolute_url(self):
        # TODO(si14): self.slug?
        return reverse('news_detail', args=[str(self.pk)])
