# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest
from django.core.exceptions import ValidationError

from learning.factories import CourseOfferingFactory, EnrollmentFactory
from learning.settings import PARTICIPANT_GROUPS, STUDENT_STATUS
from users.factories import StudentFactory, CuratorFactory, UserFactory


@pytest.mark.django_db
def test_enrolled_on_the_course():
    student = StudentFactory.create()
    co = CourseOfferingFactory()
    assert not student.enrolled_on_the_course(co.pk)
    enrollment = EnrollmentFactory(student=student, course_offering=co)
    assert student.enrolled_on_the_course(co.pk)
    curator = CuratorFactory()
    assert not curator.enrolled_on_the_course(co.pk)


@pytest.mark.django_db
def test_cached_groups(settings):
    user = UserFactory.create()
    user.groups.add(PARTICIPANT_GROUPS.STUDENT_CENTER,
                    PARTICIPANT_GROUPS.TEACHER_CENTER)
    assert set(user._cached_groups) == {PARTICIPANT_GROUPS.STUDENT_CENTER,
                                        PARTICIPANT_GROUPS.TEACHER_CENTER}
    user.status = STUDENT_STATUS.expelled
    user.groups.add(PARTICIPANT_GROUPS.VOLUNTEER)
    # Invalidate property cache
    del user._cached_groups
    # Nothing change!
    assert user._cached_groups == {PARTICIPANT_GROUPS.TEACHER_CENTER,
                                   PARTICIPANT_GROUPS.STUDENT_CENTER,
                                   PARTICIPANT_GROUPS.VOLUNTEER}
    # Add student club group for center students on club site
    user.groups.clear()
    del user._cached_groups
    user.groups.add(PARTICIPANT_GROUPS.STUDENT_CENTER)
    user.status = ''
    user.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    assert set(user._cached_groups) == {PARTICIPANT_GROUPS.STUDENT_CENTER,
                                        PARTICIPANT_GROUPS.STUDENT_CLUB}


def test_github_id_validation():
    user = UserFactory.build()
    with pytest.raises(ValidationError):
        user.github_id = "mikhail--m"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_id = "mikhailm-"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_id = "mikhailm--"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_id = "-mikhailm"
        user.clean_fields()
    user.github_id = "mikhailm"
    user.clean_fields()
    user.github_id = "mikhail-m"
    user.clean_fields()
    user.github_id = "m-i-k-h-a-i-l-m"
    user.clean_fields()
