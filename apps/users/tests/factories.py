import factory

from django.conf import settings

from core.tests.factories import BranchFactory
from learning.settings import GradeTypes
from users.constants import GenderTypes, Roles
from users.models import (
    CertificateOfParticipation, OnlineCourseRecord, SHADCourseRecord, StudentProfile,
    StudentTypes, User, UserGroup, YandexUserData
)

__all__ = ('User', 'SHADCourseRecord', 'CertificateOfParticipation',
           'OnlineCourseRecord', 'UserFactory', 'CuratorFactory',
           'StudentFactory', 'TeacherFactory', 'VolunteerFactory',
           'InvitedStudentFactory', 'OnlineCourseRecordFactory',  'StudentProfileFactory',
           'SHADCourseRecordFactory', 'CertificateOfParticipationFactory')

from users.services import assign_role


def add_user_groups(user, groups):
    for role in groups:
        user.add_group(role=role)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "testuser%04d" % n)
    gender = factory.Iterator([GenderTypes.MALE, GenderTypes.FEMALE])
    password = "test123foobar@!"
    email = factory.Sequence(lambda n: "user%04d@foobar.net" % n)
    first_name = factory.Sequence(lambda n: "Ivan%04d" % n)
    last_name = factory.Sequence(lambda n: "Petrov%04d" % n)
    branch = None
    time_zone = factory.LazyAttribute(lambda user: user.branch.time_zone if user.branch is not None else settings.DEFAULT_TIMEZONE)
    is_notification_allowed = True

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


class UserGroupFactory(factory.django.DjangoModelFactory):
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
    username = factory.Sequence(lambda n: "student%04d" % n)
    email = factory.Sequence(lambda n: "student%04d@test.email" % n)

    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        if self.branch:
            kwargs.setdefault('branch', self.branch)
        StudentProfileFactory(user=self, **kwargs)


class InvitedStudentFactory(UserFactory):
    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        if self.branch:
            kwargs.setdefault('branch', self.branch)
            # TODO fix type to StudentTypes.INVITED and wrong permission tests
        StudentProfileFactory(user=self, type=StudentTypes.VOLUNTEER, **kwargs)


class VolunteerFactory(UserFactory):

    @factory.post_generation
    def student_profile(self, create, extracted, **kwargs):
        if not create:
            return
        if self.branch:
            kwargs.setdefault('branch', self.branch)
        StudentProfileFactory(user=self, type=StudentTypes.VOLUNTEER, **kwargs)


class TeacherFactory(UserFactory):
    @factory.post_generation
    def required_groups(self, create, extracted, **kwargs):
        if not create:
            return
        site_id = kwargs.pop("site_id", None)
        self.add_group(role=Roles.TEACHER, site_id=site_id)


class StudentProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentProfile
        django_get_or_create = ('user', 'branch', 'year_of_admission')

    type = StudentTypes.REGULAR
    user = factory.SubFactory(UserFactory,
                              time_zone=factory.SelfAttribute('..branch.time_zone'))
    branch = factory.SubFactory(BranchFactory,
                                code=settings.DEFAULT_BRANCH_CODE)
    year_of_admission = factory.SelfAttribute('user.date_joined.year')

    @factory.post_generation
    def academic_disciplines(self: StudentProfile, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for academic_discipline in extracted:
                self.academic_disciplines.add(academic_discipline)

    @factory.post_generation
    def add_permissions(self: StudentProfile, create, extracted, **kwargs):
        if not create:
            return
        # FIXME: use `create_student_profile` service instead by overriding ._create factory method
        permission_role = StudentTypes.to_permission_role(self.type)
        assign_role(account=self.user, role=permission_role, site=self.site)


class OnlineCourseRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OnlineCourseRecord

    name = factory.Sequence(lambda n: "Online course %04d" % n)
    student = factory.SubFactory(StudentFactory)


class SHADCourseRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SHADCourseRecord

    name = factory.Sequence(lambda n: "SHAD course name %04d" % n)
    teachers = factory.Sequence(lambda n: "SHAD course teachers %04d" % n)
    student = factory.SubFactory(StudentFactory)
    grade = factory.Iterator(list(GradeTypes.values))
    semester = factory.SubFactory('learning.tests.factories.SemesterFactory')


class CertificateOfParticipationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CertificateOfParticipation

    signature = "FIO"
    note = ""
    student_profile = factory.SubFactory(StudentProfileFactory)

class YandexUserDataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = YandexUserData

    user = factory.SubFactory(UserFactory)
    login = factory.Sequence(lambda n: "Yandex login %04d" % n)
    uid = factory.Sequence(lambda n: "Uid %04d" % n)
    first_name = factory.Sequence(lambda n: "First name %04d" % n)
    last_name = factory.Sequence(lambda n: "Last name %04d" % n)
    display_name = factory.Sequence(lambda n: "Display name %04d" % n)
    real_name = factory.Sequence(lambda n: "Real name %04d" % n)
