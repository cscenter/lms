# -*- coding: utf-8 -*-

import factory

from learning.settings import GradeTypes
from users.constants import AcademicRoles, GenderTypes
from users.models import User, SHADCourseRecord, EnrollmentCertificate, \
    OnlineCourseRecord, UserGroup

__all__ = ('User', 'SHADCourseRecord', 'EnrollmentCertificate',
           'OnlineCourseRecord', 'UserFactory', 'CuratorFactory',
           'StudentFactory', 'StudentCenterFactory', 'StudentClubFactory',
           'TeacherCenterFactory', 'VolunteerFactory', 'ProjectReviewerFactory', 'OnlineCourseRecordFactory',
           'SHADCourseRecordFactory', 'EnrollmentCertificateFactory')


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

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            add_user_groups(self, extracted)

    @factory.post_generation
    def raw_password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = self.password
        self.set_password(raw_password)
        self.save()
        self.raw_password = raw_password

    @factory.post_generation
    def curriculum_year(self, create, extracted, **kwargs):
        if not create:
            return
        self.curriculum_year = extracted
        if not extracted and self.enrollment_year:
            self.curriculum_year = self.enrollment_year


class UserGroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = UserGroup

    user = factory.SubFactory(UserFactory)
    role = factory.Faker('random_element',
                         elements=[c for c, _ in AcademicRoles.choices])


class CuratorFactory(UserFactory):
    is_superuser = True
    is_staff = True


class StudentFactory(UserFactory):
    city_id = 'spb'
    branch = factory.SubFactory('learning.tests.factories.BranchFactory',
                                code='spb')

    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [AcademicRoles.STUDENT_CENTER,
                           AcademicRoles.STUDENT_CLUB]
        add_user_groups(self, required_groups)


class StudentCenterFactory(UserFactory):
    enrollment_year = 2015
    city_id = 'spb'
    branch = factory.SubFactory('learning.tests.factories.BranchFactory',
                                code='spb')

    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [AcademicRoles.STUDENT_CENTER]
        add_user_groups(self, required_groups)


class StudentClubFactory(UserFactory):
    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [AcademicRoles.STUDENT_CLUB]
        add_user_groups(self, required_groups)


class TeacherCenterFactory(UserFactory):
    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [AcademicRoles.TEACHER_CENTER]
        add_user_groups(self, required_groups)


class VolunteerFactory(UserFactory):
    branch = factory.SubFactory('learning.tests.factories.BranchFactory',
                                code='spb')

    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [AcademicRoles.VOLUNTEER]
        add_user_groups(self, required_groups)


class ProjectReviewerFactory(UserFactory):
    @factory.post_generation
    def _add_required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        required_groups = [AcademicRoles.PROJECT_REVIEWER]
        add_user_groups(self, required_groups)


class OnlineCourseRecordFactory(factory.DjangoModelFactory):
    class Meta:
        model = OnlineCourseRecord

    name = factory.Sequence(lambda n: "Online course %03d" % n)
    student = factory.SubFactory(UserFactory,
                                 groups=[User.roles.STUDENT_CENTER])


class SHADCourseRecordFactory(factory.DjangoModelFactory):
    class Meta:
        model = SHADCourseRecord

    name = factory.Sequence(lambda n: "SHAD course name %03d" % n)
    teachers = factory.Sequence(lambda n: "SHAD course teachers %03d" % n)
    student = factory.SubFactory(UserFactory,
                                 groups=[User.roles.STUDENT_CENTER])
    grade = factory.Iterator(list(GradeTypes.values))
    semester = factory.SubFactory('learning.tests.factories.SemesterFactory')


class EnrollmentCertificateFactory(factory.DjangoModelFactory):
    class Meta:
        model = EnrollmentCertificate

    signature = "FIO"
    note = ""
    student = factory.SubFactory(UserFactory,
                                 groups=[User.roles.STUDENT_CENTER])
