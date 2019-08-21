# -*- coding: utf-8 -*-
import factory
from django.conf import settings
from django.contrib.sites.models import Site
from post_office.models import EmailTemplate

from core.models import City, Branch, Location
from compscicenter_ru.settings.test import TEST_DOMAIN, ANOTHER_DOMAIN
from learning.settings import Branches

__all__ = ('CityFactory', 'EmailTemplateFactory', 'BranchFactory',
           'SiteFactory', 'LocationFactory', 'Location', 'Site', 'City',
           'EmailTemplate', 'Branch',)


class SiteFactory(factory.DjangoModelFactory):
    class Meta:
        model = Site
        django_get_or_create = ('domain',)

    domain = factory.Iterator(x for x in (TEST_DOMAIN, ANOTHER_DOMAIN))
    name = factory.Sequence(lambda n: "Site Name %03d" % n)


class CityFactory(factory.DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ('code',)

    code = factory.Sequence(lambda n: "%03d" % n)
    name = factory.Sequence(lambda n: "City name %03d" % n)
    abbr = factory.Sequence(lambda n: "%03d" % n)


class EmailTemplateFactory(factory.DjangoModelFactory):
    class Meta:
        model = EmailTemplate
        django_get_or_create = ["name"]


class BranchFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Branch %03d" % n)
    code = factory.Sequence(lambda n: "b%03d" % n)
    site = factory.SubFactory(SiteFactory,
                              domain=factory.LazyAttribute(lambda o: settings.TEST_DOMAIN))
    city = factory.SubFactory(CityFactory)
    order = factory.Sequence(lambda n: n)
    time_zone = 'Europe/Moscow'

    class Meta:
        model = Branch
        django_get_or_create = ('code', 'site')


class LocationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Location

    city = factory.SubFactory(CityFactory, code=Branches.SPB)
    name = factory.Sequence(lambda n: "Location %03d" % n)
    description = factory.Sequence(lambda n: "location for tests %03d" % n)
