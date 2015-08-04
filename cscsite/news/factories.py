# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime
import factory

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone

from .models import News
from core.models import City


class CityFactory(factory.DjangoModelFactory):
    class Meta:
        model = City

    code = factory.Sequence(lambda n: "COD %02d" % n)

class SiteFactory(factory.DjangoModelFactory):
    class Meta:
        model = Site


class NewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = News

    title = factory.Sequence(lambda n: "Test news %03d" % n)

    slug = factory.Sequence(lambda n: "test-news-%03d" % n)

    language = factory.List(list(code for code, name in settings.LANGUAGES))

    city = factory.SubFactory(CityFactory)
    site = factory.SubFactory(SiteFactory)

