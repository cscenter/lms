import factory
from factory.fuzzy import FuzzyInteger, FuzzyText

from apps.grading.constants import CheckingSystemTypes
from grading.models import Checker, CheckingSystem, Submission
from grading.utils import get_yandex_contest_url
from learning.models import AssignmentSubmissionTypes
from learning.tests.factories import AssignmentCommentFactory


class CheckingSystemFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Checking System %04d" % n)
    type = CheckingSystemTypes.YANDEX_CONTEST
    settings = factory.Dict({
        'access_token': FuzzyText(length=30)
    })

    class Meta:
        model = CheckingSystem


class CheckerFactory(factory.django.DjangoModelFactory):
    checking_system = factory.SubFactory(CheckingSystemFactory)
    url = factory.Sequence(lambda n: get_yandex_contest_url(n, n))
    settings = factory.Dict({
        'contest_id': FuzzyInteger(0, 100),
        'problem_id': factory.Iterator(['A', 'B', 'C', 'D'])
    })

    class Meta:
        model = Checker


class SubmissionFactory(factory.django.DjangoModelFactory):
    assignment_submission = factory.SubFactory(AssignmentCommentFactory,
                                               type=AssignmentSubmissionTypes.SOLUTION)

    class Meta:
        model = Submission
