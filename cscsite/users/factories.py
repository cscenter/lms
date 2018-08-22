# -*- coding: utf-8 -*-

import factory

from django.contrib.auth.models import Group
from learning.settings import PARTICIPANT_GROUPS, GRADES
from users.models import CSCUser, SHADCourseRecord, CSCUserReference, \
    OnlineCourseRecord


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = CSCUser

    username = factory.Sequence(lambda n: "testuser%03d" % n)
    gender = factory.Iterator([CSCUser.GENDER_MALE, CSCUser.GENDER_FEMALE])
    password = "test123foobar@!"
    email = factory.Sequence(lambda n: "user%03d@foobar.net" % n)
    first_name = factory.Sequence(lambda n: "Ivan%03d" % n)
    last_name = factory.Sequence(lambda n: "Petrov%03d" % n)

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group in extracted:
                if isinstance(group, int):
                    group_add = Group.objects.get(pk=group)
                else:
                    group_add = Group.objects.get(name=group)
                self.groups.add(group_add)

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


class CuratorFactory(UserFactory):
    is_superuser = True
    is_staff = True


class StudentFactory(UserFactory):
    city_id = 'spb'

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        groups = extracted or [PARTICIPANT_GROUPS.STUDENT_CENTER,
                               PARTICIPANT_GROUPS.STUDENT_CLUB]
        for group in groups:
            self.groups.add(group)


class StudentCenterFactory(UserFactory):
    enrollment_year = 2015
    city_id = 'spb'

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        groups = extracted or [PARTICIPANT_GROUPS.STUDENT_CENTER]
        for group in groups:
            self.groups.add(group)


class StudentClubFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        groups = extracted or [PARTICIPANT_GROUPS.STUDENT_CLUB]
        for group in groups:
            self.groups.add(group)


class TeacherCenterFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        groups = extracted or [PARTICIPANT_GROUPS.TEACHER_CENTER]
        for group in groups:
            self.groups.add(group)


class VolunteerFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        groups = extracted or [PARTICIPANT_GROUPS.VOLUNTEER]
        for group in groups:
            self.groups.add(group)


class GraduateFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        groups = extracted or [PARTICIPANT_GROUPS.GRADUATE_CENTER]
        for group in groups:
            self.groups.add(group)


class ProjectReviewerFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        groups = extracted or [PARTICIPANT_GROUPS.PROJECT_REVIEWER]
        for group in groups:
            self.groups.add(group)


class OnlineCourseRecordFactory(factory.DjangoModelFactory):
    class Meta:
        model = OnlineCourseRecord

    name = factory.Sequence(lambda n: "Online course %03d" % n)
    student = factory.SubFactory(UserFactory,
                                 groups=[CSCUser.group.STUDENT_CENTER])


class SHADCourseRecordFactory(factory.DjangoModelFactory):
    class Meta:
        model = SHADCourseRecord

    name = factory.Sequence(lambda n: "SHAD course name %03d" % n)
    teachers = factory.Sequence(lambda n: "SHAD course teachers %03d" % n)
    student = factory.SubFactory(UserFactory,
                                 groups=[CSCUser.group.STUDENT_CENTER])
    grade = factory.Iterator(list(x[0] for x in GRADES))
    semester = factory.SubFactory('learning.factories.SemesterFactory')


class CSCUserReferenceFactory(factory.DjangoModelFactory):
    class Meta:
        model = CSCUserReference

    signature = "FIO"
    note = ""
    student = factory.SubFactory(UserFactory,
                                 groups=[CSCUser.group.STUDENT_CENTER])
