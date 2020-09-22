import factory

from contests.models import CheckingSystem


class CheckingSystemFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Checking System %03d" % n)

    class Meta:
        model = CheckingSystem