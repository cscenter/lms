# -*- coding: utf-8 -*-

import datetime

import factory
from django.conf import settings
from django.utils import timezone

from core.tests.factories import BranchFactory, LocationFactory
from courses.models import StudentGroupTypes
from courses.tests.factories import *
from learning.models import StudentAssignment, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    CourseNewsNotification, Event, GraduateProfile, Invitation, \
    CourseInvitation, StudentGroup
from learning.services import StudentGroupService
from users.constants import Roles
from users.models import UserGroup
from users.tests.factories import UserFactory, StudentFactory, \
    StudentProfileFactory

__all__ = ('StudentGroupFactory', 'StudentAssignmentFactory',
           'AssignmentCommentFactory', 'EnrollmentFactory', 'InvitationFactory',
           'CourseInvitationFactory', 'AssignmentNotificationFactory',
           'CourseNewsNotificationFactory', 'EventFactory',
           'StudentAssignment', 'Enrollment', 'AssignmentComment',
           'GraduateProfileFactory')


class StudentGroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = StudentGroup

    type = StudentGroupTypes.MANUAL
    name = factory.Sequence(lambda n: "Group Name %03d" % n)
    course = factory.SubFactory(CourseFactory)


# FIXME: create enrollment
class StudentAssignmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = StudentAssignment

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(StudentFactory)


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

    student = factory.SubFactory(StudentFactory)
    student_profile = factory.SubFactory(
        StudentProfileFactory,
        user=factory.SelfAttribute('..student'),
        branch=factory.SelfAttribute('..student.branch'))
    course = factory.SubFactory(CourseFactory)

    @factory.post_generation
    def student_group(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.student_group = extracted
        else:
            self.student_group = StudentGroupService.resolve(self.course,
                                                             self.student,
                                                             settings.SITE_ID)


class InvitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Invitation

    name = factory.Sequence(lambda n: "Invitation Name %03d" % n)
    semester = factory.SubFactory(SemesterFactory)
    branch = factory.SubFactory(BranchFactory)

    @factory.post_generation
    def courses(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for course in extracted:
                self.courses.add(course)


class CourseInvitationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseInvitation

    course = factory.SubFactory(CourseFactory)
    invitation = factory.SubFactory(
        InvitationFactory,
        semester_id=factory.SelfAttribute('..course.semester_id'))


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

    venue = factory.SubFactory(LocationFactory)
    branch = factory.SubFactory('core.tests.factories.BranchFactory',
                                code=settings.DEFAULT_BRANCH_CODE)
    name = factory.Sequence(lambda n: "Test event %03d" % n)
    description = factory.Sequence(lambda n: "Test event description %03d" % n)
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = "13:00"
    ends_at = "13:45"


class GraduateFactory(UserFactory):
    graduate_profile = factory.RelatedFactory(
        'learning.tests.factories.GraduateProfileFactory',
        'student'
    )

    @factory.post_generation
    def required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        site_id = kwargs.pop("site_id", None)
        self.add_group(role=Roles.GRADUATE, site_id=site_id)

    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        StudentProfileFactory(user=self, **kwargs)
        UserGroup.objects.filter(role=Roles.STUDENT, user=self).delete()


class GraduateProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = GraduateProfile

    student = factory.SubFactory(GraduateFactory, graduate_profile=None)
    graduated_on = factory.Faker('future_date', end_date="+10d", tzinfo=None)
