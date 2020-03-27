import datetime

import pytest

from core.tests.factories import BranchFactory
from courses.models import Course, CourseClass
from courses.tests.factories import CourseFactory, CourseClassFactory
from learning.settings import Branches


@pytest.mark.django_db
def test_course_manager_available_in_branch():
    course = CourseFactory()
    branch1, branch2 = BranchFactory.create_batch(2)
    course.additional_branches.add(branch1)
    course.additional_branches.add(branch2)
    course.additional_branches.add(course.branch)
    assert Course.objects.available_in(branch1.pk).count() == 1
    assert Course.objects.available_in(course.branch_id).count() == 1


@pytest.mark.skip("TODO: Add guard to the Course.additional_branches.through model and deny to save main branch as an additional")
@pytest.mark.django_db
def test_course_class_manager_in_branches():
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_xxx = BranchFactory()
    course = CourseFactory(branch=branch_spb)
    course.additional_branches.add(branch_nsk, branch_xxx)
    date_on = datetime.date(year=2018, month=1, day=1)
    starts_at = datetime.time(hour=12, minute=0)
    cc1 = CourseClassFactory(course=course, date=date_on, starts_at=starts_at)
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 1
    # Make sure no duplicates even if course root branch added as additional
    course.additional_branches.add(branch_spb)
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 1
    course2 = CourseFactory(branch=branch_nsk)
    assert course2.pk > course.pk
    # This class is goes earlier than `cc1`
    cc2 = CourseClassFactory(course=course2,
                             date=date_on - datetime.timedelta(days=1),
                             starts_at=starts_at)
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 1
    course2.additional_branches.add(branch_spb)
    classes = list(CourseClass.objects.in_branches(branch_spb.pk))
    assert len(classes) == 2
    assert classes[0] == cc2
    assert classes[1] == cc1

