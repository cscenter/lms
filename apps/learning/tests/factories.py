import datetime

import factory

from django.conf import settings
from django.utils import timezone

from core.tests.factories import BranchFactory, LocationFactory, SiteFactory
from courses.models import StudentGroupTypes
from courses.tests.factories import *
from learning.models import (
    AssignmentComment, AssignmentNotification, AssignmentSubmissionTypes,
    CourseInvitation, CourseNewsNotification, Enrollment, EnrollmentPeriod, Event,
    GraduateProfile, Invitation, StudentAssignment, StudentGroup, StudentGroupAssignee
)
from learning.services import StudentGroupService, recreate_assignments_for_student
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import UserGroup
from users.tests.factories import StudentFactory, StudentProfileFactory, UserFactory

__all__ = ('StudentGroupFactory', 'StudentAssignmentFactory',
           'AssignmentCommentFactory', 'EnrollmentPeriodFactory',
           'EnrollmentFactory', 'InvitationFactory',
           'CourseInvitationFactory', 'AssignmentNotificationFactory',
           'CourseNewsNotificationFactory', 'EventFactory',
           'StudentAssignment', 'EnrollmentPeriod', 'Enrollment',
           'AssignmentComment', 'GraduateProfileFactory')


class StudentGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentGroup

    type = StudentGroupTypes.MANUAL
    name = factory.Sequence(lambda n: "Group Name %03d" % n)
    course = factory.SubFactory(CourseFactory)


class StudentGroupAssigneeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentGroupAssignee

    student_group = factory.SubFactory(StudentGroupFactory)
    assignee = factory.SubFactory(CourseTeacherFactory)


class StudentAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentAssignment

    assignment = factory.SubFactory(AssignmentFactory)
    student = factory.SubFactory(StudentFactory)

    @factory.post_generation
    def create_enrollment(self, create, extracted, **kwargs):
        if not create:
            return
        try:
            Enrollment.objects.get(course=self.assignment.course,
                                   student=self.student)
        except Enrollment.DoesNotExist:
            EnrollmentFactory(course=self.assignment.course,
                              student=self.student)


class AssignmentCommentFactory(factory.django.DjangoModelFactory):
    """
    Make sure to call refresh_from_db if logic depends on
    `first_student_comment_at` or `last_comment_from`.
    """
    class Meta:
        model = AssignmentComment

    student_assignment = factory.SubFactory(StudentAssignmentFactory)
    text = factory.Sequence(lambda n: "Test comment %03d" % n)
    author = factory.SubFactory(UserFactory)
    type = AssignmentSubmissionTypes.COMMENT
    attached_file = factory.django.FileField()


class EnrollmentPeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EnrollmentPeriod
        django_get_or_create = ('semester', 'site')

    site = factory.SubFactory(SiteFactory)
    semester = factory.SubFactory(SemesterFactory)


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    student = factory.SubFactory(StudentFactory)
    student_profile = factory.SubFactory(
        StudentProfileFactory,
        user=factory.SelfAttribute('..student'),
        branch=factory.SelfAttribute('..course.main_branch'))
    course = factory.SubFactory(CourseFactory)

    @factory.post_generation
    def recreate_assignments(self, create, extracted, **kwargs):
        if not create:
            return
        recreate_assignments_for_student(self)

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


class InvitationFactory(factory.django.DjangoModelFactory):
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


class CourseInvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseInvitation

    course = factory.SubFactory(CourseFactory)
    invitation = factory.SubFactory(
        InvitationFactory,
        semester_id=factory.SelfAttribute('..course.semester_id'))


class AssignmentNotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssignmentNotification

    user = factory.SubFactory(UserFactory)
    student_assignment = factory.SubFactory(StudentAssignmentFactory)


class CourseNewsNotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseNewsNotification

    user = factory.SubFactory(UserFactory)
    course_offering_news = factory.SubFactory(CourseNewsFactory)


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    venue = factory.SubFactory(LocationFactory)
    branch = factory.SubFactory('core.tests.factories.BranchFactory',
                                code=settings.DEFAULT_BRANCH_CODE)
    name = factory.Sequence(lambda n: "Test event %03d" % n)
    description = factory.Sequence(lambda n: "Test event description %03d" % n)
    date = (datetime.datetime.now().replace(tzinfo=timezone.utc)
            + datetime.timedelta(days=3)).date()
    starts_at = datetime.time(hour=13, minute=0)
    ends_at = datetime.time(hour=13, minute=45)


class GraduateFactory(UserFactory):
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
        kwargs['status'] = StudentStatuses.GRADUATE
        student_profile = StudentProfileFactory(user=self, **kwargs)
        self.__student_profile_id = student_profile.pk
        UserGroup.objects.filter(role=Roles.STUDENT, user=self).delete()

    @factory.post_generation
    def graduate_profile(self, create, extracted, **kwargs):
        if not create:
            return
        GraduateProfileFactory(student_profile_id=self.__student_profile_id)


class GraduateProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GraduateProfile

    student_profile = factory.SubFactory(StudentProfileFactory,
                                         status=StudentStatuses.GRADUATE)
    graduated_on = factory.Faker('future_date', end_date="+10d", tzinfo=None)
