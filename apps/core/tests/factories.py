# -*- coding: utf-8 -*-
import factory
import pytz
from post_office.models import EmailTemplate

from django.conf import settings
from django.contrib.sites.models import Site

from core.models import Branch, City, Location, SiteConfiguration, University
from core.tests.settings import TEST_DOMAIN
from learning.settings import Branches

__all__ = ('CityFactory', 'EmailTemplateFactory', 'BranchFactory',
           'SiteFactory', 'LocationFactory', 'Location', 'Site', 'City',
           'EmailTemplate', 'Branch',)


class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site
        django_get_or_create = ('domain',)

    domain = TEST_DOMAIN
    name = factory.Sequence(lambda n: "Site Name %04d" % n)
    # TODO: create default site configuration


class SiteConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteConfiguration
        django_get_or_create = ('site',)

    site = factory.SubFactory(SiteFactory)
    enabled = True
    lms_domain = 'my.example.com'
    default_branch_code = 'spb'
    default_from_email = 'noreply@example.com'
    email_backend = settings.EMAIL_BACKEND
    email_host = settings.EMAIL_HOST
    email_host_password = SiteConfiguration.encrypt('password')
    email_host_user = factory.Sequence(lambda n: "User_%04d" % n)
    email_port = settings.EMAIL_PORT
    email_use_tls = False
    email_use_ssl = False


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ('code',)

    code = factory.Sequence(lambda n: "%04d" % n)
    name = factory.Sequence(lambda n: "City name %04d" % n)
    abbr = factory.Sequence(lambda n: "%04d" % n)

    @factory.lazy_attribute
    def time_zone(self):
        if self.code == Branches.NSK:
            return pytz.timezone('Asia/Novosibirsk')
        else:
            return pytz.timezone('Europe/Moscow')


class EmailTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailTemplate
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: "email-template-%04d" % n)


class BranchFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Branch %04d" % n)
    code = factory.Sequence(lambda n: "b%04d" % n)
    site = factory.SubFactory(SiteFactory,
                              domain=factory.LazyAttribute(lambda o: TEST_DOMAIN))
    city = factory.SubFactory(CityFactory)
    order = factory.Sequence(lambda n: n)
    established = 1990
    active = True

    @factory.lazy_attribute
    def time_zone(self):
        if self.code != Branches.DISTANCE:
            return self.city.time_zone
        return pytz.timezone('Europe/Moscow')

    class Meta:
        model = Branch
        django_get_or_create = ('code', 'site')


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    city = factory.SubFactory(CityFactory, code=Branches.SPB)
    name = factory.Sequence(lambda n: "Location %04d" % n)
    description = factory.Sequence(lambda n: "location for tests %04d" % n)


class LegacyUniversityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = University

    name = factory.Sequence(lambda n: "University %04d" % n)
    city = factory.SubFactory(CityFactory)
