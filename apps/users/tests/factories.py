import factory

from django.conf import settings

from core.tests.factories import BranchFactory
from learning.settings import GradeTypes
from users.constants import GenderTypes, Roles, TShirtSizeTypes
from users.models import (
    CertificateOfParticipation, OnlineCourseRecord, PartnerTag, SHADCourseRecord, StudentProfile,
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

    username = factory.Sequence(lambda n: f"testuser{n}")
    gender = factory.Iterator([GenderTypes.MALE, GenderTypes.FEMALE])
    password = "test123foobar@!"
    email = factory.Sequence(lambda n: f"user{n}@foobar.net")
    first_name = factory.Sequence(lambda n: f"Ivan{n}")
    last_name = factory.Sequence(lambda n: f"Petrov{n}")
    branch = None
    time_zone = factory.LazyAttribute(lambda user: user.branch.time_zone if user.branch is not None else settings.DEFAULT_TIMEZONE)
    is_notification_allowed = True
    tshirt_size = factory.Iterator(TShirtSizeTypes.labels.values())

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
        
    # @factory.post_generation
    # def yandex_data(self, create, extracted, **kwargs):
    #     if not create:
    #         return
    #     if extracted:
            # YandexUserDataFactory(user=self)


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
    username = factory.Sequence(lambda n: f"student{n}")
    email = factory.Sequence(lambda n: f"student{n}@test.email")

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
        StudentProfileFactory(user=self, type=StudentTypes.INVITED, **kwargs)


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
        django_get_or_create = ('type', 'user', 'branch', 'year_of_admission')

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

    name = factory.Sequence(lambda n: f"Online course {n}")
    student = factory.SubFactory(StudentFactory)


class SHADCourseRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SHADCourseRecord

    name = factory.Sequence(lambda n: f"SHAD course name {n}")
    teachers = factory.Sequence(lambda n: f"SHAD course teachers {n}")
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
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    login = factory.Sequence(lambda n: f"yandex_login_{n}")
    uid = factory.Sequence(lambda n: f"uid_{n}")  # Required field, must be unique
    first_name = factory.Sequence(lambda n: f"First name {n}")
    last_name = factory.Sequence(lambda n: f"Last name {n}")
    display_name = factory.Sequence(lambda n: f"Display name {n}")
    real_name = factory.Sequence(lambda n: f"Real name {n}")

    @classmethod
    def create_batch(cls, size, **kwargs):
        # Could not find better way. This is only for creating a batch
        if 'user__sequence' in kwargs:
            users = kwargs.pop('user__sequence')
            return [cls.create(user=user, **kwargs) for user in users]
        return super().create_batch(size, **kwargs)

class PartnerTagFactory(factory.django.DjangoModelFactory):
    
    class Meta:
        model = PartnerTag
        
    name = factory.Sequence(lambda n: f"Partner name {n}")
    slug = factory.Sequence(lambda n: f"Partner slug {n}")
