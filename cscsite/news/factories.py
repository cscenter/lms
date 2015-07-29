# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime
import factory

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone

from .models import News


class NewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = News

    title = factory.Sequence(lambda n: "Test news %03d" % n)

    slug = factory.Sequence(lambda n: "test-news-%03d" % n)

    language = factory.List(list(code for code, name in settings.LANGUAGES))

    @factory.post_generation
    def sites(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            for site in extracted:
                self.sites.add(site)

    @factory.post_generation
    def cities(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for city in extracted:
                self.cities.add(city)
