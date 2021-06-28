import datetime
import random

import factory
import pytz
from factory.fuzzy import FuzzyInteger, FuzzyNaiveDateTime

from django.db.models.signals import post_save
from django.utils import timezone

from admission.constants import WHERE_DID_YOU_LEARN, InterviewFormats
from admission.models import (
    Applicant, Campaign, Comment, Contest, Exam, Interview, InterviewAssignment,
    InterviewFormat, InterviewInvitation, InterviewSlot, InterviewStream, Test
)
from admission.signals import post_save_interview
from core.tests.factories import (
    BranchFactory, EmailTemplateFactory, LocationFactory, UniversityFactory
)
from learning.settings import AcademicDegreeLevels
from users.constants import Roles
from users.tests.factories import UserFactory, add_user_groups


class FuzzyTime(FuzzyNaiveDateTime):
    def fuzz(self):
        dt = super().fuzz()
        return dt.time()


class CampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Campaign

    year = factory.LazyAttribute(lambda o: o.application_ends_at.year)
    branch = factory.SubFactory(BranchFactory)
    online_test_max_score = FuzzyInteger(30, 40)
    online_test_passing_score = FuzzyInteger(20, 25)
    exam_max_score = FuzzyInteger(30, 40)
    exam_passing_score = FuzzyInteger(20, 25)
    application_starts_at = factory.Faker('past_datetime',
                                          start_date="-10d",
                                          tzinfo=timezone.utc)
    application_ends_at = factory.Faker('future_datetime', end_date="+30d",
                                        tzinfo=timezone.utc)


class ApplicantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Applicant

    campaign = factory.SubFactory(CampaignFactory)
    first_name = factory.Sequence(lambda n: "Name %03d" % n)
    patronymic = factory.Sequence(lambda n: "Patronymic %03d" % n)
    last_name = factory.Sequence(lambda n: "Surname %03d" % n)
    email = factory.Sequence(lambda n: "user%03d@foobar.net" % n)
    phone = factory.Sequence(lambda n: '123-555-%04d' % n)
    university = factory.SubFactory(UniversityFactory)
    yandex_login = factory.Sequence(lambda n: "yandex_login_%03d" % n)
    faculty = factory.Sequence(lambda n: "faculty_%03d" % n)
    level_of_education = factory.fuzzy.FuzzyChoice([x for x, _ in
                                                    AcademicDegreeLevels.choices])
    where_did_you_learn = factory.fuzzy.FuzzyChoice([x for x, _ in
                                                     WHERE_DID_YOU_LEARN])


class ContestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contest

    campaign = factory.SubFactory(CampaignFactory)
    contest_id = factory.Sequence(lambda n: "%04d" % n)
    # file?


class TestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Test

    applicant = factory.SubFactory(ApplicantFactory)
    score = factory.Sequence(lambda n: "%02d" % n)


class ExamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exam

    applicant = factory.SubFactory(ApplicantFactory)
    score = factory.Sequence(lambda n: "%02d" % n)


class InterviewAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewAssignment

    campaign = factory.SubFactory(CampaignFactory)
    name = factory.Sequence(lambda n: "Assignment Name %03d" % n)
    description = factory.Sequence(lambda n: "Assignment Name %03d" % n)


class InterviewerFactory(UserFactory):
    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [Roles.INTERVIEWER]
        add_user_groups(self, required_groups)


class InterviewFormatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewFormat
        django_get_or_create = ('campaign', 'format')

    format = InterviewFormats.OFFLINE
    campaign = factory.SubFactory(CampaignFactory)
    reminder_template = factory.SubFactory(EmailTemplateFactory)
    remind_before_start = '1 00:00:00'  # 1 day


class InterviewFactory(factory.django.DjangoModelFactory):
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


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    interview = factory.SubFactory(InterviewFactory)
    interviewer = factory.SubFactory(InterviewerFactory)
    score = factory.Iterator(range(-2, 3))


class InterviewStreamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewStream

    campaign = factory.SubFactory(CampaignFactory)
    format = InterviewFormats.OFFLINE
    interview_format = factory.SubFactory(
        InterviewFormatFactory,
        campaign=factory.SelfAttribute('..campaign'),
        format=factory.SelfAttribute('..format'))
    venue = factory.SubFactory(
        LocationFactory,
        city=factory.SelfAttribute('..campaign.branch.city'))

    date = factory.Faker('future_date', end_date="+10d")
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


class InterviewSlotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewSlot

    interview = factory.SubFactory(InterviewFactory)
    stream = factory.SubFactory(InterviewStreamFactory)


class InterviewInvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewInvitation

    applicant = factory.SubFactory(ApplicantFactory)
    interview = factory.SubFactory(InterviewFactory,
                                   applicant=factory.SelfAttribute('..applicant'))
    expired_at = factory.Faker('date_time_between',
                               start_date="now", end_date="+30d",
                               tzinfo=timezone.utc)

    @factory.post_generation
    def streams(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for stream in extracted:
                self.streams.add(stream)
