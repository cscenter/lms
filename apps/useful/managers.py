from django.db import models
from django.db.models import query


class UsefulQuerySet(query.QuerySet):
    def for_site(self, site_id):
        return self.filter(site=site_id)

    def with_tag(self, tag):
        """
        Currently one tag is used for specifying category for Useful items.
        If multiple tags will be used for filtering, be aware of possible duplicates in the queryset!
        """
        return self.filter(tags__name=tag)


UsefulDefaultManager = models.Manager.from_queryset(UsefulQuerySet)
