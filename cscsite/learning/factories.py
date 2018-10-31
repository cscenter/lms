# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import datetime

import factory
from django.utils import timezone
from django.utils.timezone import now
from factory import CREATE_STRATEGY

from core.models import City
from learning.models import MetaCourse, Semester, Course, \
    Assignment, Venue, CourseClass, CourseClassAttachment, StudentAssignment, \
    AssignmentComment, Enrollment, AssignmentNotification, \
    AssignmentAttachment, CourseNews, \
    CourseOfferingNewsNotification, NonCourseEvent, CourseTeacher, \
    AreaOfStudy
from learning.settings import PARTICIPANT_GROUPS, SEMESTER_TYPES
from users.factories import UserFactory, StudentCenterFactory
from .utils import get_current_term_pair, get_term_by_index


class MetaCourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = MetaCourse

    name = factory.Sequence(lambda n: "Test course %03d" % n)
    slug = factory.Sequence(lambda n: "test-course-%03d" % n)
    description = "This a course for testing purposes"


class SemesterFactory(factory.DjangoModelFactory):
    class Meta:
        model = Semester
        django_get_or_create = ('year', 'type')

    year = 2015
    type = factory.Iterator(['spring', 'autumn'])

    @classmethod
    def create_current(cls, **kwargs):
        """Get or create semester for current term"""
        city_code = kwargs.pop('city_code', 'spb')
        year, type = get_current_term_pair(city_code)
        kwargs.pop('year', None)
        kwargs.pop('type', None)
        return cls.create(year=year, type=type, **kwargs)

    @classmethod
    def create_next(cls, term):
        """Get or create term model which following this one"""
        year, next_term = get_term_by_index(term.index + 1)
        return cls.create(year=year, type=next_term)

    @classmethod
    def create_prev(cls, term):
        """Get or create term model which following this one"""
        year, prev_term = get_term_by_index(term.index - 1)
        return cls.create(year=year, type=prev_term)


class CourseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Course

    meta_course = factory.SubFactory(MetaCourseFactory)
    semester = factory.SubFactory(SemesterFactory)
    description = "This course offering will be very different"

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

    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for teacher in extracted:
                CourseTeacher(course_offering=self,
                              teacher=teacher,
                              notify_by_default=True).save()


class CourseTeacherFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseTeacher

    teacher = factory.SubFactory(UserFactory)
    course_offering = factory.SubFactory(CourseFactory)
    roles = CourseTeacher.roles.lecturer


class CourseNewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseNews

    course_offering = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: "Imporant news about testing %03d" % n)
    author = factory.SubFactory(UserFactory, groups=['Teacher [CENTER]'])
    text = factory.Sequence(lambda n: ("Suddenly it turned out that testing "
                                       "(%03d) can be useful!" % n))


class VenueFactory(factory.DjangoModelFactory):
    class Meta:
        model = Venue

    city = factory.Iterator(City.objects.all())
    name = factory.Sequence(lambda n: "Test venue %03d" % n)
    description = factory.Sequence(lambda n: "special venue for tests %03d" % n)


class AreaOfStudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = AreaOfStudy

    name = factory.Sequence(lambda n: "Study area %03d" % n)
    code = factory.Sequence(lambda n: "p%01d" % n)


class CourseClassFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseClass

    course_offering = factory.SubFactory(CourseFactory)
    venue = factory.SubFactory(
        VenueFactory,
        city=factory.SelfAttribute('..course_offering.city'))
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

    course_offering = factory.SubFactory(CourseFactory)
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
            ts = self.course_offering.course_teachers.all()
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
    student = factory.SubFactory(StudentCenterFactory)


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
    course_offering = factory.SubFactory(CourseFactory)


class AssignmentNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentNotification

    user = factory.SubFactory(UserFactory)
    student_assignment = factory.SubFactory(StudentAssignmentFactory)


class CourseNewsNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingNewsNotification

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
