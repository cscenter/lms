import factory

from universities.models import City, Country, Faculty, University


class CountryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Country%04d" % n)

    class Meta:
        model = Country
        django_get_or_create = ('name',)


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ('external_id',)

    country = factory.SubFactory(CountryFactory)
    external_id = factory.Sequence(lambda n: "%04d" % n)
    name = factory.Sequence(lambda n: "City Name %04d" % n)
    display_name = factory.Sequence(lambda n: "City Display Name %04d" % n)


class UniversityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = University
        django_get_or_create = ('external_id',)

    city = factory.SubFactory(CityFactory)
    external_id = factory.Sequence(lambda n: "%04d" % n)
    name = factory.Sequence(lambda n: "Uni Name %04d" % n)
    display_name = factory.Sequence(lambda n: "Uni Display Name %04d" % n)


class FacultyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Faculty
        django_get_or_create = ('external_id',)

    university = factory.SubFactory(UniversityFactory)
    external_id = factory.Sequence(lambda n: "%04d" % n)
    name = factory.Sequence(lambda n: "Faculty Name %04d" % n)
    display_name = factory.Sequence(lambda n: "Faculty Display Name %04d" % n)
