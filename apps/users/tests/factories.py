# -*- coding: utf-8 -*-

import factory
from django.conf import settings

from core.tests.factories import BranchFactory
from learning.settings import GradeTypes, Branches
from users.constants import Roles, GenderTypes
from users.models import User, SHADCourseRecord, CertificateOfParticipation, \
    OnlineCourseRecord, UserGroup, StudentProfile, StudentTypes

__all__ = ('User', 'SHADCourseRecord', 'CertificateOfParticipation',
           'OnlineCourseRecord', 'UserFactory', 'CuratorFactory',
           'StudentFactory', 'TeacherFactory', 'VolunteerFactory',
           'OnlineCourseRecordFactory',
           'SHADCourseRecordFactory', 'CertificateOfParticipationFactory')


def add_user_groups(user, groups):
    for role in groups:
        user.add_group(role=role)


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "testuser%03d" % n)
    gender = factory.Iterator([GenderTypes.MALE, GenderTypes.FEMALE])
    password = "test123foobar@!"
    email = factory.Sequence(lambda n: "user%03d@foobar.net" % n)
    first_name = factory.Sequence(lambda n: "Ivan%03d" % n)
    last_name = factory.Sequence(lambda n: "Petrov%03d" % n)
    branch = factory.SubFactory('core.tests.factories.BranchFactory',
                                code=settings.DEFAULT_BRANCH_CODE)
    time_zone = factory.SelfAttribute('branch.time_zone')

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            site_id = kwargs.pop("site_id", None)
            for role in extracted:
                self.add_group(role=role, site_id=site_id)

    @factory.post_generation
    def raw_password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = self.password
        self.set_password(raw_password)
        self.save()
        self.raw_password = raw_password


class UserGroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = UserGroup

    user = factory.SubFactory(UserFactory)
    role = factory.Faker('random_element',
                         elements=[c for c, _ in Roles.choices])


class CuratorFactory(UserFactory):
    is_staff = True
    is_superuser = True

    @factory.post_generation
    def required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        site_id = kwargs.pop("site_id", None)
        self.add_group(role=Roles.CURATOR, site_id=site_id)


class StudentFactory(UserFactory):
    """
    Student access role will be created by student profile post save signal
    """
    username = factory.Sequence(lambda n: "student%03d" % n)
    email = factory.Sequence(lambda n: "student%03d@test.email" % n)

    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        kwargs.setdefault('branch', self.branch)
        StudentProfileFactory(user=self, **kwargs)


class InvitedStudentFactory(UserFactory):
    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        kwargs.setdefault('branch', self.branch)
        StudentProfileFactory(user=self, type=StudentTypes.VOLUNTEER, **kwargs)


class VolunteerFactory(UserFactory):

    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        kwargs.setdefault('branch', self.branch)
        StudentProfileFactory(user=self, type=StudentTypes.VOLUNTEER, **kwargs)


class TeacherFactory(UserFactory):
    @factory.post_generation
    def required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        site_id = kwargs.pop("site_id", None)
        self.add_group(role=Roles.TEACHER, site_id=site_id)


class StudentProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = StudentProfile
        django_get_or_create = ('user', 'branch', 'year_of_admission')

    type = StudentTypes.REGULAR
    user = factory.SubFactory(UserFactory,
                              time_zone=factory.SelfAttribute('..branch.time_zone'))
    branch = factory.SubFactory(BranchFactory)
    year_of_admission = factory.SelfAttribute('user.date_joined.year')


class OnlineCourseRecordFactory(factory.DjangoModelFactory):
    class Meta:
        model = OnlineCourseRecord

    name = factory.Sequence(lambda n: "Online course %03d" % n)
    student = factory.SubFactory(StudentFactory)


class SHADCourseRecordFactory(factory.DjangoModelFactory):
    class Meta:
        model = SHADCourseRecord

    name = factory.Sequence(lambda n: "SHAD course name %03d" % n)
    teachers = factory.Sequence(lambda n: "SHAD course teachers %03d" % n)
    student = factory.SubFactory(StudentFactory)
    grade = factory.Iterator(list(GradeTypes.values))
    semester = factory.SubFactory('learning.tests.factories.SemesterFactory')


class CertificateOfParticipationFactory(factory.DjangoModelFactory):
    class Meta:
        model = CertificateOfParticipation

    signature = "FIO"
    note = ""
    student_profile = factory.SubFactory(StudentProfileFactory)
