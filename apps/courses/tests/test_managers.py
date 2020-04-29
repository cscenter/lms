import datetime

import pytest

from core.tests.factories import BranchFactory
from courses.models import Course, CourseClass, CourseBranch
from courses.tests.factories import CourseFactory, CourseClassFactory
from learning.settings import Branches


@pytest.mark.django_db
def test_course_manager_available_in_branch():
    main_branch, branch1, branch2 = BranchFactory.create_batch(3)
    course = CourseFactory(main_branch=main_branch,
                           branches=[branch1, branch2, main_branch])
    assert Course.objects.available_in(branch1.pk).count() == 1
    assert Course.objects.available_in(course.main_branch_id).count() == 1


@pytest.mark.django_db
def test_course_class_manager_in_branches():
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_xxx = BranchFactory()
    course = CourseFactory(main_branch=branch_spb,
                           branches=[branch_nsk, branch_xxx])
    cc1 = CourseClassFactory(course=course)
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 1
    course2 = CourseFactory(main_branch=branch_nsk)
    assert course2.pk > course.pk
    cc2 = CourseClassFactory(course=course2)

    # Course2 was not shared with SPB branch yet
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 1

    # Share course2 with SPB branch
    CourseBranch(course=course2, branch=branch_spb).save()
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 2

    # No duplicates even if looking for courses in several branches
    classes = list(CourseClass.objects.in_branches(branch_spb.pk, branch_nsk.pk))
    assert len(classes) == 2


@pytest.mark.django_db
def test_course_class_manager_sort_order():
    branch_spb = BranchFactory(code=Branches.SPB)
    course1 = CourseFactory(main_branch=branch_spb)
    course2 = CourseFactory(main_branch=branch_spb)
    date_on = datetime.date(year=2018, month=1, day=1)
    starts_at = datetime.time(hour=12, minute=0)
    cc1 = CourseClassFactory(course=course1, date=date_on, starts_at=starts_at)
    cc2 = CourseClassFactory(course=course2,
                             date=date_on + datetime.timedelta(days=1),
                             starts_at=starts_at)
    assert CourseClass.objects.in_branches(branch_spb.pk).count() == 2
    classes = list(CourseClass.objects.in_branches(branch_spb.pk))
    # Course classes are sorted by date DESC, course ASC, starts_at DESC (see CourseClass.Meta)
    # So cc2 should be the first class in the list
    assert classes[0] == cc2
    assert classes[1] == cc1


