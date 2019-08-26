import pytest

from core.tests.factories import BranchFactory
from courses.models import Course
from courses.tests.factories import CourseFactory


@pytest.mark.django_db
def test_course_manager_available_in_branch():
    course = CourseFactory()
    branch1, branch2 = BranchFactory.create_batch(2)
    course.additional_branches.add(branch1)
    course.additional_branches.add(branch2)
    course.additional_branches.add(course.branch)
    assert Course.objects.available_in(branch1).count() == 1
    assert Course.objects.available_in(course.branch).count() == 1
