from django.db import models
from django.core.urlresolvers import reverse

class Event(models.Model):
    # author = foo
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=30,
                            help_text="short underscore-separated string " \
                                "for human-readable URLs, as in " \
                                "test.com/events/<b>important_event</b>/",
                            unique=True)
    notification_text = models.TextField(max_length=140,
                                         help_text="this text is used in " \
                                             "notifications, 140 symbols max")
    event_text = models.TextField(max_length=(1024 * 2),
                                  help_text="this text is used on the site, " \
                                      "2kb max")
    email_text = models.TextField(max_length=(1024 * 4),
                                  help_text="this text is used in emails, " \
                                      "4kb max")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    # for_groups = foo

    def __unicode__(self):
        # return u"%s (%s)" % (self.title, self.author)
        return u"%s" % (self.slug)

    def get_absolute_url(self):
        # TODO(si14): self.slug?
        return reverse('event_detail', args=[str(self.pk)])
