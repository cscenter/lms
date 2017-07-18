# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime

import factory
from django.utils import timezone
from django.utils.timezone import now

from core.models import City
from learning.models import Course, Semester, CourseOffering, \
    Assignment, Venue, CourseClass, CourseClassAttachment, StudentAssignment, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    AssignmentAttachment, CourseOfferingNews, \
    CourseOfferingNewsNotification, NonCourseEvent, CourseOfferingTeacher, \
    AreaOfStudy, next_term_starts_at
from learning.settings import PARTICIPANT_GROUPS, SEMESTER_TYPES
from users.factories import UserFactory
from .utils import get_current_semester_pair, get_term_by_index


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Sequence(lambda n: "Test course %03d" % n)
    slug = factory.Sequence(lambda n: "test-course-%03d" % n)
    description = "This a course for testing purposes"


class SemesterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Semester
        django_get_or_create = ('year', 'type')

    year = 2015
    type = Semester.TYPES.spring

    @classmethod
    def create_current(cls, **kwargs):
        """Get or create semester for current term"""
        year, type = get_current_semester_pair()
        kwargs.pop('year', None)
        kwargs.pop('type', None)
        return cls.create(year=year, type=type, **kwargs)

    @classmethod
    def create_next(cls, term):
        """Get or create term model which following this one"""
        year, next_term = get_term_by_index(term.index + 1)
        return cls.create(year=year, type=next_term)


class CourseOfferingFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOffering

    course = factory.SubFactory(CourseFactory)
    semester = factory.SubFactory(SemesterFactory)
    description = "This course offering will be very different"

    @classmethod
    def create(cls, **kwargs):
        attrs = cls.attributes(create=True, extra=kwargs)
        if "completed_at" not in kwargs:
            term = attrs["semester"]
            attrs["completed_at"] = term.ends_at + datetime.timedelta(days=1)
        return cls._generate(True, attrs)

    @factory.post_generation
    def city(self, create, extracted, **kwargs):
        """ Allow to pass City instance or PK """
        if not create:
            return
        if extracted:
            if isinstance(extracted, City):
                self.city = extracted
            else:
                self.city = City.objects.get(pk=extracted)

    # TODO: add "enrolled students" here
    # TODO: create course offering for current semester by default

    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for teacher in extracted:
                CourseOfferingTeacher(course_offering=self,
                                      teacher=teacher,
                                      notify_by_default=True).save()


class CourseOfferingTeacherFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingTeacher

    teacher = factory.SubFactory(UserFactory)
    course_offering = factory.SubFactory(CourseOfferingFactory)
    roles = CourseOfferingTeacher.roles.lecturer


class CourseOfferingNewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingNews

    course_offering = factory.SubFactory(CourseOfferingFactory)
    title = factory.Sequence(lambda n: "Imporant news about testing %03d" % n)
    author = factory.SubFactory(UserFactory, groups=['Teacher [CENTER]'])
    text = factory.Sequence(lambda n: ("Suddenly it turned out that testing "
                                       "(%03d) can be useful!" % n))


class VenueFactory(factory.DjangoModelFactory):
    class Meta:
        model = Venue

    # TODO: make sure city_id is one from `settings.TIME_ZONES`
    name = "Test venue"
    description = "This is a special venue for tests"


class AreaOfStudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = AreaOfStudy

    name = factory.Sequence(lambda n: "Study area %03d" % n)
    code = factory.Sequence(lambda n: "p%01d" % n)


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
    class Meta:
        model = Assignment

    course_offering = factory.SubFactory(CourseOfferingFactory)
    deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                   + datetime.timedelta(days=1))
    is_online = True
    title = factory.Sequence(lambda n: "Test assignment %03d" % n)
    text = "This is a text for a test assignment"
    grade_min = 10
    grade_max = 80

    @factory.post_generation
    def notify_teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for co_teacher in extracted:
                self.notify_teachers.add(co_teacher)
        else:
            ts = self.course_offering.courseofferingteacher_set.all()
            for t in ts:
                self.notify_teachers.add(t)


class AssignmentAttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentAttachment

    assignment = factory.SubFactory(AssignmentFactory)
    attachment = factory.django.FileField()


class StudentAssignmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = StudentAssignment

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(UserFactory, groups=['Student [CENTER]'])


class AssignmentCommentFactory(factory.DjangoModelFactory):
    """
    Make sure to call refresh_from_db if logic depends on
    `first_submission_at` or `last_comment_from`.
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
                                 groups=[PARTICIPANT_GROUPS.STUDENT_CENTER])
    course_offering = factory.SubFactory(CourseOfferingFactory)


class AssignmentNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentNotification

    user = factory.SubFactory(UserFactory)
    student_assignment = factory.SubFactory(StudentAssignmentFactory)


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
