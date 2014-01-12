from django.db import models
from django.core.urlresolvers import reverse

class Event(models.Model):
    # author = foo
    # title = foo
    slug = models.SlugField(max_length=30)
    # notification_text = models.TextField()
    event_text = models.TextField()
    # email_text = models.TextField()
    # for_groups = foo

    def __unicode__(self):
        # return u"%s (%s)" % (self.title, self.author)
        return u"%s" % (self.slug)

    def get_absolute_url(self):
        # TODO(si14): self.slug?
        return reverse('event_detail', args=[str(self.pk)])
