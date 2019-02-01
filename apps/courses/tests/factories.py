import datetime

import factory
from django.utils import timezone

from core.models import City
from courses.models import MetaCourse, Semester, Course, CourseTeacher, \
    CourseNews, CourseClass, CourseClassAttachment, Assignment, \
    AssignmentAttachment, Venue
from courses.utils import get_current_term_pair, get_term_by_index
from users.tests.factories import TeacherCenterFactory

__all__ = (
    "MetaCourseFactory", "SemesterFactory", "VenueFactory", "CourseFactory",
    "CourseNewsFactory", "AssignmentFactory", "CourseTeacherFactory",
    "CourseClassFactory", "CourseClassAttachmentFactory",
    "AssignmentAttachmentFactory"
)


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


class VenueFactory(factory.DjangoModelFactory):
    class Meta:
        model = Venue

    city = factory.Iterator(City.objects.all())
    name = factory.Sequence(lambda n: "Test venue %03d" % n)
    description = factory.Sequence(lambda n: "special venue for tests %03d" % n)


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
                CourseTeacher(course=self,
                              teacher=teacher,
                              notify_by_default=True).save()


class CourseTeacherFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseTeacher

    teacher = factory.SubFactory(TeacherCenterFactory)
    course = factory.SubFactory(CourseFactory)
    roles = CourseTeacher.roles.lecturer


class CourseNewsFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseNews

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: "Important news about testing %03d" % n)
    author = factory.SubFactory(TeacherCenterFactory)
    text = factory.Sequence(lambda n: ("Suddenly it turned out that testing "
                                       "(%03d) can be useful!" % n))


class CourseClassFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseClass

    course = factory.SubFactory(CourseFactory)
    venue = factory.SubFactory(
        VenueFactory,
        city=factory.SelfAttribute('..course.city'))
    type = 'lecture'
    name = factory.Sequence(lambda n: "Test class %03d" % n)
    description = factory.Sequence(
        lambda n: "In this class %03d we will test" % n)
    slides = factory.django.FileField()
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = datetime.time(hour=13, minute=0)
    ends_at = datetime.time(hour=13, minute=45)

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

    course = factory.SubFactory(CourseFactory)
    deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                   + datetime.timedelta(days=1))
    is_online = True
    title = factory.Sequence(lambda n: "Test assignment %03d" % n)
    text = "This is a text for a test assignment"
    passing_score = 10
    maximum_score = 80

    @factory.post_generation
    def notify_teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for co_teacher in extracted:
                self.notify_teachers.add(co_teacher)
        else:
            ts = self.course.course_teachers.all()
            for t in ts:
                self.notify_teachers.add(t)


class AssignmentAttachmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = AssignmentAttachment

    assignment = factory.SubFactory(AssignmentFactory)
    attachment = factory.django.FileField()
