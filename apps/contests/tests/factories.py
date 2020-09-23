import factory
from factory.fuzzy import FuzzyText, FuzzyInteger

from contests.models import CheckingSystem, Checker
from contests.utils import get_yandex_contest_problem_url


class CheckingSystemFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Checking System %03d" % n)
    settings = factory.Dict({
        'access_token': FuzzyText(length=30)
    })

    class Meta:
        model = CheckingSystem


class CheckerFactory(factory.django.DjangoModelFactory):
    checking_system = factory.SubFactory(CheckingSystemFactory)
    url = factory.Sequence(lambda n: get_yandex_contest_problem_url(n, n))
    settings = factory.Dict({
        'contest_id': FuzzyInteger(0, 100),
        'problem_id': factory.Iterator(['A', 'B', 'C', 'D'])
    })

    class Meta:
        model = Checker
