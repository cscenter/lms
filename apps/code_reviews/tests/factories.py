import factory

from code_reviews.models import GerritChange
from core.tests.factories import SiteFactory
from learning.tests.factories import StudentAssignmentFactory


class GerritChangeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GerritChange

    student_assignment = factory.SubFactory(StudentAssignmentFactory)
    site = factory.SubFactory(SiteFactory)
    change_id = factory.Sequence(lambda n: "change~%03d" % n)
