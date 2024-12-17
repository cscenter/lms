import datetime

import factory
import pytz

from django.conf import settings
from django.utils import timezone

from core.tests.factories import BranchFactory, LocationFactory
from courses.constants import AssigneeMode, AssignmentFormat, MaterialVisibilityTypes
from courses.models import (
    Assignment, AssignmentAttachment, Course, CourseBranch, CourseClass,
    CourseClassAttachment, CourseNews, CourseReview, CourseTeacher, LearningSpace,
    MetaCourse, Semester
)
from courses.services import CourseService
from courses.utils import get_current_term_pair, get_term_by_index
from learning.services import AssignmentService
from users.tests.factories import TeacherFactory

__all__ = (
    "MetaCourseFactory", "SemesterFactory", "CourseFactory",
    "CourseNewsFactory", "AssignmentFactory", "CourseTeacherFactory",
    "CourseClassFactory", "CourseClassAttachmentFactory",
    "AssignmentAttachmentFactory", "CourseReviewFactory",
)


class MetaCourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MetaCourse

    name = factory.Sequence(lambda n: "Test course %04d" % n)
    slug = factory.Sequence(lambda n: "test-course-%04d" % n)
    description = "This a course for testing purposes"


class SemesterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Semester
        django_get_or_create = ('year', 'type')

    year = 2015
    type = factory.Iterator(['spring', 'autumn'])

    @factory.post_generation
    def enrollment_period(self, create, extracted, **kwargs):
        from learning.tests.factories import EnrollmentPeriodFactory
        if not create:
            return
        kwargs.pop("semester", None)
        EnrollmentPeriodFactory(semester=self, **kwargs)

    @classmethod
    def create_current(cls, **kwargs):
        """Get or create semester for current term"""
        branch_code = kwargs.pop('for_branch', settings.DEFAULT_BRANCH_CODE)
        branch = BranchFactory(code=branch_code)
        term_pair = get_current_term_pair(branch.get_timezone())
        kwargs.pop('year', None)
        kwargs.pop('type', None)
        return cls.create(year=term_pair.year, type=term_pair.type, **kwargs)

    @classmethod
    def create_next(cls, term: Semester):
        """Get or create term model which following this one"""
        term_pair = get_term_by_index(term.index + 1)
        return cls.create(year=term_pair.year, type=term_pair.type)

    @classmethod
    def create_prev(cls, term):
        """Get or create term model which following this one"""
        term_pair = get_term_by_index(term.index - 1)
        return cls.create(year=term_pair.year, type=term_pair.type)


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    meta_course = factory.SubFactory(MetaCourseFactory)
    semester = factory.SubFactory(SemesterFactory)
    description = "This course offering will be very different"
    main_branch = factory.SubFactory(BranchFactory,
                                     code=settings.DEFAULT_BRANCH_CODE)
    # Too many tests are done assumed is_draft = False as they were done before draft was invented
    is_draft = False

    @factory.post_generation
    def teachers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for teacher in extracted:
                CourseTeacher(course=self,
                              teacher=teacher,
                              notify_by_default=True).save()

    @factory.post_generation
    def branches(self, create, extracted, **kwargs):
        """
        Main branch will be added by `sync_branches` post generation hook, so
        it's possible to omit main branch in this list
        """
        if not create:
            return
        if extracted:
            for branch in extracted:
                CourseBranch(course=self, branch=branch).save()

    @factory.post_generation
    def sync_branches(self, create, extracted, **kwargs):
        if not create:
            return
        CourseService.sync_branches(self)


class CourseTeacherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseTeacher

    teacher = factory.SubFactory(TeacherFactory)
    course = factory.SubFactory(CourseFactory)


class CourseReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseReview

    course = factory.SubFactory(CourseFactory)
    text = factory.Sequence(lambda n: ("Course Review %04d" % n))


class CourseNewsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseNews

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: "Important news about testing %04d" % n)
    author = factory.SubFactory(TeacherFactory)
    text = factory.Sequence(lambda n: ("Suddenly it turned out that testing "
                                       "(%04d) can be useful!" % n))


class LearningSpaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LearningSpace

    location = factory.SubFactory(LocationFactory)
    branch = factory.SubFactory(BranchFactory)


class CourseClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseClass

    course = factory.SubFactory(CourseFactory)
    venue = factory.SubFactory(
        LearningSpaceFactory,
        branch=factory.SelfAttribute('..course.main_branch'))
    type = 'lecture'
    name = factory.Sequence(lambda n: "Test class %04d" % n)
    description = factory.Sequence(
        lambda n: "In this class %04d we will test" % n)
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = datetime.time(hour=13, minute=0)
    ends_at = datetime.time(hour=13, minute=45)
    time_zone = factory.LazyAttribute(lambda o: o.course.main_branch.get_timezone())
    materials_visibility = MaterialVisibilityTypes.PARTICIPANTS

    @factory.post_generation
    def restricted_to(self, create, extracted, **kwargs):
        if extracted:
            for student_group in extracted:
                self.restricted_to.add(student_group)


class CourseClassAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseClassAttachment

    course_class = factory.SubFactory(CourseClassFactory)
    material = factory.django.FileField()


class AssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assignment

    course = factory.SubFactory(CourseFactory)
    deadline_at = factory.Faker('date_time_between', start_date="+1d",
                                end_date="+10d", tzinfo=pytz.UTC)
    submission_type = AssignmentFormat.ONLINE
    title = factory.Sequence(lambda n: "Test assignment %04d" % n)
    text = "This is a text for a test assignment"
    time_zone = factory.LazyAttribute(lambda o: o.course.main_branch.get_timezone())
    passing_score = 10
    maximum_score = 80
    weight = 1
    assignee_mode = AssigneeMode.MANUAL

    @factory.post_generation
    def restricted_to(self, create, extracted, **kwargs):
        if extracted:
            for student_group in extracted:
                self.restricted_to.add(student_group)

    # Note: this hook depends on `.restricted_to` values and must be
    # declared after `restricted_to` hook
    @factory.post_generation
    def generate_student_assignments(self, create, extracted, **kwargs):
        if create:
            AssignmentService.bulk_create_student_assignments(self)

    @factory.post_generation
    def assignees(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for co_teacher in extracted:
                self.assignees.add(co_teacher)


class AssignmentAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssignmentAttachment

    assignment = factory.SubFactory(AssignmentFactory)
    attachment = factory.django.FileField()
