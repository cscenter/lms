import datetime
import random
from itertools import count

import factory
import pytz
from django.db.models.signals import post_save
from django.utils import timezone
from factory.fuzzy import FuzzyInteger, FuzzyNaiveDateTime, FuzzyDate

from core.factories import UniversityFactory
from core.models import City
from admission.models import Campaign, Applicant, Contest, Test, \
    Exam, InterviewAssignment, Interview, Comment, \
    InterviewSlot, InterviewStream, InterviewInvitation
from admission.signals import post_save_interview
from courses.tests.factories import VenueFactory
from users.constants import AcademicRoles
from users.factories import UserFactory


class FuzzyTime(FuzzyNaiveDateTime):
    def fuzz(self):
        dt = super().fuzz()
        return dt.time()


class CampaignFactory(factory.DjangoModelFactory):
    class Meta:
        model = Campaign

    year = factory.Iterator(count(start=2015))
    city = factory.Iterator(City.objects.all())
    online_test_max_score = FuzzyInteger(30, 40)
    online_test_passing_score = FuzzyInteger(20, 25)
    exam_max_score = FuzzyInteger(30, 40)
    exam_passing_score = FuzzyInteger(20, 25)
    application_ends_at = factory.Faker('date_time_between',
                                        start_date="now", end_date="+30d",
                                        tzinfo=timezone.utc)


class ApplicantFactory(factory.DjangoModelFactory):
    class Meta:
        model = Applicant

    campaign = factory.SubFactory(CampaignFactory)
    first_name = factory.Sequence(lambda n: "Name %03d" % n)
    patronymic = factory.Sequence(lambda n: "Patronymic %03d" % n)
    surname = factory.Sequence(lambda n: "Surname %03d" % n)
    email = factory.Sequence(lambda n: "user%03d@foobar.net" % n)
    phone = factory.Sequence(lambda n: '123-555-%04d' % n)
    university = factory.SubFactory(UniversityFactory)


class ContestFactory(factory.DjangoModelFactory):
    class Meta:
        model = Contest

    campaign = factory.SubFactory(CampaignFactory)
    contest_id = factory.Sequence(lambda n: "%04d" % n)
    # file?


class TestFactory(factory.DjangoModelFactory):
    class Meta:
        model = Test

    applicant = factory.SubFactory(ApplicantFactory)
    score = factory.Sequence(lambda n: "%02d" % n)


class ExamFactory(factory.DjangoModelFactory):
    class Meta:
        model = Exam

    applicant = factory.SubFactory(ApplicantFactory)
    score = factory.Sequence(lambda n: "%02d" % n)


class InterviewAssignmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = InterviewAssignment

    campaign = factory.SubFactory(CampaignFactory)
    name = factory.Sequence(lambda n: "Assignment Name %03d" % n)
    description = factory.Sequence(lambda n: "Assignment Name %03d" % n)


class InterviewerFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        groups = extracted or [AcademicRoles.INTERVIEWER]
        for group in groups:
            self.groups.add(group)


class InterviewFactory(factory.DjangoModelFactory):
    class Meta:
        model = Interview

    applicant = factory.SubFactory(ApplicantFactory)
    # TODO: replace with FuzzyDate
    date = (datetime.datetime.now().replace(tzinfo=pytz.UTC)
            + datetime.timedelta(days=3))

    @factory.post_generation
    def interviewers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for interviewer in extracted:
                self.interviewers.add(interviewer)

    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        """
        When any RelatedFactory or post_generation attribute is defined
        on the DjangoModelFactory subclass, a second save() is
        performed after the call to _create().
        """
        post_save.disconnect(post_save_interview, Interview)
        super(InterviewFactory, cls)._after_postgeneration(obj, create, results)
        post_save.connect(post_save_interview, Interview)


class CommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Comment

    interview = factory.SubFactory(InterviewFactory)
    interviewer = factory.SubFactory(InterviewerFactory)
    score = factory.Iterator(range(-2, 3))


class InterviewStreamFactory(factory.DjangoModelFactory):
    class Meta:
        model = InterviewStream

    #
    venue = factory.SubFactory(VenueFactory,
                               city=factory.SelfAttribute('..campaign.city'))
    campaign = factory.SubFactory(CampaignFactory)
    date = FuzzyDate(datetime.date(2011, 1, 1))
    # 13:00 - 15:00
    start_at = FuzzyTime(datetime.datetime(2011, 1, 1, 13, 0, 0),
                         datetime.datetime(2011, 1, 1, 15, 0, 0))
    # 16:00 - 17:00
    end_at = FuzzyTime(datetime.datetime(2011, 1, 1, 16, 0, 0),
                       datetime.datetime(2011, 1, 1, 17, 0, 0))
    with_assignments = random.choice([True, False])

    @factory.post_generation
    def interviewers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for interviewer in extracted:
                self.interviewers.add(interviewer)


class InterviewSlotFactory(factory.DjangoModelFactory):
    class Meta:
        model = InterviewSlot

    interview = factory.SubFactory(InterviewFactory)
    stream = factory.SubFactory(InterviewStreamFactory)


class InterviewInvitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = InterviewInvitation

    applicant = factory.SubFactory(ApplicantFactory)
    interview = factory.SubFactory(InterviewFactory)
    expired_at = factory.Faker('date_time_between',
                               start_date="now", end_date="+30d",
                               tzinfo=timezone.utc)
