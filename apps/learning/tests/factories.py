# -*- coding: utf-8 -*-

import datetime

import factory
from django.utils import timezone

from core.factories import CityFactory
from courses.tests.factories import *
from learning.models import StudentAssignment, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    CourseNewsNotification, Event, Branch, GraduateProfile
from learning.settings import Branches
from study_programs.models import AcademicDiscipline
from users.tests.factories import UserFactory, StudentCenterFactory, \
    GraduateFactory

__all__ = ('AcademicDisciplineFactory', 'StudentAssignmentFactory',
           'AssignmentCommentFactory', 'EnrollmentFactory',
           'AssignmentNotificationFactory', 'BranchFactory',
           'CourseNewsNotificationFactory', 'EventFactory',
           'StudentAssignment', 'Enrollment', 'AssignmentComment', 'Branch',
           'GraduateProfileFactory')


class BranchFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Branch %03d" % n)
    code = factory.Iterator(x for x, _ in Branches.choices)

    class Meta:
        model = Branch
        django_get_or_create = ('code',)


class AcademicDisciplineFactory(factory.DjangoModelFactory):
    class Meta:
        model = AcademicDiscipline

    name = factory.Sequence(lambda n: "Study area %03d" % n)
    code = factory.Sequence(lambda n: "p%01d" % n)


# FIXME: create enrollment
class StudentAssignmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = StudentAssignment

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(StudentCenterFactory)


class AssignmentCommentFactory(factory.DjangoModelFactory):
    """
    Make sure to call refresh_from_db if logic depends on
    `first_student_comment_at` or `last_comment_from`.
    """
    class Meta:
        model = AssignmentComment

    student_assignment = factory.SubFactory(StudentAssignmentFactory)
    text = factory.Sequence(lambda n: "Test comment %03d" % n)
    author = factory.SubFactory(UserFactory)
    attached_file = factory.django.FileField()


class EnrollmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Enrollment

    student = factory.SubFactory(StudentCenterFactory)
    course = factory.SubFactory(CourseFactory)


class AssignmentNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentNotification

    user = factory.SubFactory(UserFactory)
    student_assignment = factory.SubFactory(StudentAssignmentFactory)


class CourseNewsNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseNewsNotification

    user = factory.SubFactory(UserFactory)
    course_offering_news = factory.SubFactory(CourseNewsFactory)


class EventFactory(factory.DjangoModelFactory):
    class Meta:
        model = Event

    venue = factory.SubFactory(VenueFactory)
    name = factory.Sequence(lambda n: "Test event %03d" % n)
    description = factory.Sequence(lambda n: "Test event description %03d" % n)
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = "13:00"
    ends_at = "13:45"


class GraduateProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = GraduateProfile

    student = factory.SubFactory(GraduateFactory)
    graduated_on = factory.Faker('future_date', end_date="+10d", tzinfo=None)
