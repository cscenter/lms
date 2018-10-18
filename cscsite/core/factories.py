# -*- coding: utf-8 -*-
import factory
from post_office.models import EmailTemplate

from .models import University, City


class CityFactory(factory.DjangoModelFactory):
    class Meta:
        model = City

    code = factory.Sequence(lambda n: "%03d" % n)
    name = factory.Sequence(lambda n: "City name %03d" % n)
    abbr = factory.Sequence(lambda n: "%03d" % n)


class UniversityFactory(factory.DjangoModelFactory):
    class Meta:
        model = University

    name = factory.Sequence(lambda n: "University name %03d" % n)
    city = factory.SubFactory(CityFactory)


class EmailTemplateFactory(factory.DjangoModelFactory):
    class Meta:
        model = EmailTemplate
        django_get_or_create = ["name"]
