# -*- coding: utf-8 -*-
import factory
from django.conf import settings
from django.contrib.sites.models import Site
from post_office.models import EmailTemplate

from core.models import City, Branch, Location, SiteConfiguration
from learning.settings import Branches

__all__ = ('CityFactory', 'EmailTemplateFactory', 'BranchFactory',
           'SiteFactory', 'LocationFactory', 'Location', 'Site', 'City',
           'EmailTemplate', 'Branch',)


class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site
        django_get_or_create = ('domain',)

    domain = settings.TEST_DOMAIN
    name = factory.Sequence(lambda n: "Site Name %03d" % n)


class SiteConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteConfiguration
        django_get_or_create = ('site',)

    site = factory.SubFactory(SiteFactory)
    enabled = True
    lms_subdomain = 'my'
    default_branch_code = 'spb'
    default_from_email = 'noreply@example.com'
    email_backend = settings.EMAIL_BACKEND
    email_host = settings.EMAIL_HOST
    email_host_password = SiteConfiguration.encrypt('password')
    email_host_user = factory.Sequence(lambda n: "User_%03d" % n)
    email_port = settings.EMAIL_PORT
    email_use_tls = False
    email_use_ssl = False


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ('code',)

    code = factory.Sequence(lambda n: "%03d" % n)
    name = factory.Sequence(lambda n: "City name %03d" % n)
    abbr = factory.Sequence(lambda n: "%03d" % n)

    @factory.lazy_attribute
    def time_zone(self):
        if self.code == Branches.NSK:
            return 'Asia/Novosibirsk'
        else:
            return 'Europe/Moscow'


class EmailTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailTemplate
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: "email-template-%03d" % n)


class BranchFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Branch %03d" % n)
    code = factory.Sequence(lambda n: "b%03d" % n)
    site = factory.SubFactory(SiteFactory,
                              domain=factory.LazyAttribute(lambda o: settings.TEST_DOMAIN))
    city = factory.SubFactory(CityFactory)
    order = factory.Sequence(lambda n: n)
    established = 2013
    active = True

    @factory.lazy_attribute
    def time_zone(self):
        if self.code != Branches.DISTANCE:
            return self.city.time_zone
        else:
            return 'Europe/Moscow'

    class Meta:
        model = Branch
        django_get_or_create = ('code', 'site')


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    city = factory.SubFactory(CityFactory, code=Branches.SPB)
    name = factory.Sequence(lambda n: "Location %03d" % n)
    description = factory.Sequence(lambda n: "location for tests %03d" % n)
