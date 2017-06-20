# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import uuid
from itertools import count

import datetime
import factory
from django.db.models.signals import post_save
from factory.fuzzy import FuzzyInteger, FuzzyDateTime

from django.utils import timezone

from core.factories import UniversityFactory, CityFactory
from learning.admission.models import Campaign, Applicant, Contest, Test, \
    Exam, InterviewAssignment, Interview, Comment, \
    InterviewSlot, InterviewStream
from learning.admission.signals import post_save_interview
from learning.factories import VenueFactory
from learning.settings import PARTICIPANT_GROUPS
from users.factories import UserFactory


class CampaignFactory(factory.DjangoModelFactory):
    class Meta:
        model = Campaign

    year = factory.Iterator(count(start=2015))
    city = factory.SubFactory(CityFactory)
    online_test_max_score = FuzzyInteger(30, 40)
    online_test_passing_score = FuzzyInteger(20, 25)
    exam_max_score = FuzzyInteger(30, 40)
    exam_passing_score = FuzzyInteger(20, 25)


class ApplicantFactory(factory.DjangoModelFactory):
    class Meta:
        model = Applicant

    campaign = factory.SubFactory(CampaignFactory)
    first_name = factory.Sequence(lambda n: "Name %03d" % n)
    patronymic = factory.Sequence(lambda n: "Patronymic %03d" % n)
    surname = factory.Sequence(lambda n: "Surname %03d" % n)
    email = factory.Sequence(lambda n: "user%03d@foobar.net" % n)
    phone = factory.Sequence(lambda n: '123-555-%04d' % n)
    uuid = factory.LazyFunction(uuid.uuid4)
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
    groups = [PARTICIPANT_GROUPS.INTERVIEWER]


class InterviewFactory(factory.DjangoModelFactory):
    class Meta:
        model = Interview

    applicant = factory.SubFactory(ApplicantFactory)
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()

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

    venue = factory.SubFactory(VenueFactory)


class InterviewSlotFactory(factory.DjangoModelFactory):
    class Meta:
        model = InterviewSlot

    interview = factory.SubFactory(InterviewFactory)
    stream = factory.SubFactory(InterviewStreamFactory)
