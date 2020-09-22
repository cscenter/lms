import factory

from contests.models import CheckingSystem, Checker


class CheckingSystemFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Checking System %03d" % n)

    class Meta:
        model = CheckingSystem


class CheckerFactory(factory.django.DjangoModelFactory):
    checking_system = factory.SubFactory(CheckingSystemFactory)
    url = factory.Sequence(lambda n:
                           'https://contest.yandex.ru/contest/%s/problems/%s'
                           % (n, n))
    settings = factory.Sequence(lambda n: {'contest_id': n,
                                           'problem_id': n})

    class Meta:
        model = Checker
