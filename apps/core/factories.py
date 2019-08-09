# -*- coding: utf-8 -*-
import factory
from post_office.models import EmailTemplate

from .models import City


class CityFactory(factory.DjangoModelFactory):
    class Meta:
        model = City

    code = factory.Sequence(lambda n: "%03d" % n)
    name = factory.Sequence(lambda n: "City name %03d" % n)
    abbr = factory.Sequence(lambda n: "%03d" % n)


class EmailTemplateFactory(factory.DjangoModelFactory):
    class Meta:
        model = EmailTemplate
        django_get_or_create = ["name"]
