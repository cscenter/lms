# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime
from django.contrib.auth.models import Group
from django.utils import timezone

import factory

from learning.models import Course, Semester, CourseOffering, CourseOfferingNews, \
    Assignment, Venue, CourseClass, CourseClassAttachment, AssignmentStudent, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    AssignmentAttachment, \
    CourseOfferingNewsNotification, NonCourseEvent, StudentProject
from users.models import CSCUser


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = CSCUser

    username = factory.Sequence(lambda n: "testuser%03d" % n)
    password = "test123foobar@!"
    email = "user@foobar.net"
    first_name = factory.Sequence(lambda n: "Ivan%03d" % n)
    last_name = factory.Sequence(lambda n: "Petrov%03d" % n)

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group_name in extracted:
                self.groups.add(Group.objects.get(name=group_name))

    @factory.post_generation
    def raw_password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = self.password
        self.set_password(raw_password)
        self.save()
        self.raw_password = raw_password


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Sequence(lambda n: "Test course %03d" % n)
    slug = factory.Sequence(lambda n: "test-course-%03d" % n)
    description = "This a course for testing purposes"


class SemesterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Semester

    year = 2015
    type = Semester().TYPES['spring']


class CourseOfferingFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOffering

    course = factory.SubFactory(CourseFactory)
    semester = factory.SubFactory(SemesterFactory)
    description = "This course offering will be very different"

    # TODO: add "enrolled students" here
    # TODO: create course offering for current semester by default

    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for teacher in extracted:
                self.teachers.add(teacher)


class CourseOfferingNewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingNews

    course_offering = factory.SubFactory(CourseOfferingFactory)
    title = factory.Sequence(lambda n: "Imporant news about testing %03d" % n)
    author = factory.SubFactory(UserFactory, groups=['Teacher'])
    text = factory.Sequence(lambda n: ("Suddenly it turned out that testing "
                                       "(%03d) can be useful!" % n))


class VenueFactory(factory.DjangoModelFactory):
    class Meta:
        model = Venue

    name = "Test venue"
    description = "This is a special venue for tests"


class CourseClassFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseClass

    course_offering = factory.SubFactory(CourseOfferingFactory)
    venue = factory.SubFactory(VenueFactory)
    type = 'lecture'
    name = factory.Sequence(lambda n: "Test class %03d" % n)
    description = factory.Sequence(
        lambda n: "In this class %03d we will test" % n)
    slides = factory.django.FileField()
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = "13:00"
    ends_at = "13:45"

    @classmethod
    def build(cls, *args, **kwargs):
        if all('slides_' not in key for key in kwargs.keys()):
            kwargs['slides'] = None
        return super(CourseClassFactory, cls).build(*args, **kwargs)

    @classmethod
    def create(cls, *args, **kwargs):
        if all('slides_' not in key for key in kwargs.keys()):
            kwargs['slides'] = None
        return super(CourseClassFactory, cls).create(*args, **kwargs)


class CourseClassAttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseClassAttachment

    course_class = factory.SubFactory(CourseClassFactory)
    material = factory.django.FileField()


class AssignmentFactory(factory.DjangoModelFactory):
    # Note(Sergey Zh): implicitly create AssignmentStudent record through assigned_to
    class Meta:
        model = Assignment

    course_offering = factory.SubFactory(CourseOfferingFactory)
    # TODO(Dmitry): add assigned_to
    deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                   + datetime.timedelta(days=1))
    is_online = True
    title = factory.Sequence(lambda n: "Test assignment %03d" % n)
    text = "This is a text for a test assignment"
    grade_min = 10
    grade_max = 80


class AssignmentAttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentAttachment

    assignment = factory.SubFactory(AssignmentFactory)
    attachment = factory.django.FileField()


class AssignmentStudentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentStudent

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory, groups=['Student'])


class AssignmentCommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentComment

    assignment_student = factory.SubFactory(AssignmentStudentFactory)
    text = factory.Sequence(lambda n: "Test comment %03d" % n)
    author = factory.SubFactory(UserFactory)
    attached_file = factory.django.FileField()


class EnrollmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Enrollment

    student = factory.SubFactory(UserFactory, groups=['Student'])
    course_offering = factory.SubFactory(CourseOfferingFactory)


class AssignmentNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentNotification

    user = factory.SubFactory(UserFactory)
    assignment_student = factory.SubFactory(AssignmentStudentFactory)


class CourseOfferingNewsNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingNewsNotification

    user = factory.SubFactory(UserFactory)
    course_offering_news = factory.SubFactory(CourseOfferingNewsFactory)


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


class StudentProjectFactory(factory.DjangoModelFactory):
    class Meta:
        model = StudentProject

    name = factory.Sequence(lambda n: "Test student project %03d" % n)
    description = factory.Sequence(lambda n: ("Test student project "
                                              "description %03d" % n))
    student = factory.SubFactory(UserFactory, groups=['Student'])
    supervisor = factory.Sequence(lambda n: "Test supervisor %03d" % n)
    project_type = 'practice'

    @factory.post_generation
    def semesters(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for semester in extracted:
                self.semesters.add(semester)
