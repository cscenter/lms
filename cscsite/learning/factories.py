# -*- coding: utf-8 -*-

import datetime

import factory
from django.utils import timezone

from courses.factories import *
from learning.models import StudentAssignment, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    CourseNewsNotification, NonCourseEvent, AreaOfStudy
from learning.settings import AcademicRoles
from users.factories import UserFactory, StudentCenterFactory


class AreaOfStudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = AreaOfStudy

    name = factory.Sequence(lambda n: "Study area %03d" % n)
    code = factory.Sequence(lambda n: "p%01d" % n)


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

    student = factory.SubFactory(UserFactory,
                                 groups=[AcademicRoles.STUDENT_CENTER])
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


class NonCourseEventFactory(factory.DjangoModelFactory):
    class Meta:
        model = NonCourseEvent

    venue = factory.SubFactory(VenueFactory)
    name = factory.Sequence(lambda n: "Test event %03d" % n)
    description = factory.Sequence(lambda n: "Test event description %03d" % n)
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = "13:00"
    ends_at = "13:45"
