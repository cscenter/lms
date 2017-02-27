# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import uuid
from itertools import count

import datetime
import factory
from factory.fuzzy import FuzzyInteger

from django.utils import timezone

from core.factories import UniversityFactory
from learning.admission.models import Campaign, Applicant, Contest, Test, \
    Exam, InterviewAssignment, Interview, Comment
from learning.settings import PARTICIPANT_GROUPS
from users.factories import UserFactory


class CampaignFactory(factory.DjangoModelFactory):
    class Meta:
        model = Campaign

    year = factory.Iterator(count(start=2015))
    online_test_max_score = FuzzyInteger(30, 40)
    online_test_passing_score = FuzzyInteger(20, 25)
    exam_max_score = FuzzyInteger(30, 40)
    exam_passing_score = FuzzyInteger(20, 25)


class ApplicantFactory(factory.DjangoModelFactory):
    class Meta:
        model = Applicant

    campaign = factory.SubFactory(CampaignFactory)
    first_name = factory.Sequence(lambda n: "Name %03d" % n)
    last_name = factory.Sequence(lambda n: "Patronymic %03d" % n)
    second_name = factory.Sequence(lambda n: "Surname %03d" % n)
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
    # TODO: add interviewers, set status


class CommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Comment

    interview = factory.SubFactory(InterviewFactory)
    interviewer = factory.SubFactory(InterviewerFactory)
    score = factory.Iterator(range(-2, 3))
