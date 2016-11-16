# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest

from learning.factories import CourseOfferingFactory, EnrollmentFactory
from users.factories import StudentFactory, CuratorFactory


@pytest.mark.django_db
def test_enrolled_on_the_course():
    student = StudentFactory.create()
    co = CourseOfferingFactory()
    assert not student.enrolled_on_the_course(co.pk)
    enrollment = EnrollmentFactory(student=student, course_offering=co)
    assert student.enrolled_on_the_course(co.pk)
    curator = CuratorFactory()
    assert not curator.enrolled_on_the_course(co.pk)
