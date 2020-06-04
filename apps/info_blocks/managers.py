from django.db import models
from django.db.models import query


class InfoBlockQuerySet(query.QuerySet):
    def for_site(self, site_id):
        return self.filter(site=site_id)

    def with_tag(self, slug: str):
        return self.filter(tags__slug=slug)


InfoBlockDefaultManager = models.Manager.from_queryset(InfoBlockQuerySet)
