import pytest

from core.tests.factories import BranchFactory
from core.tests.settings import TEST_DOMAIN_ID
from courses.tests.factories import CourseClassFactory, CourseFactory
from learning.selectors import get_classes, get_teacher_classes
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_get_teacher_classes_should_not_return_duplicate_classes(settings):
    branch1, branch2 = BranchFactory.create_batch(2)
    t = TeacherFactory(branch=branch1,
                       required_groups__site_id=TEST_DOMAIN_ID)
    course = CourseFactory(teachers=[t],
                           main_branch=branch1,
                           branches=[branch1, branch2])
    assert len(course.branches.all()) == 2
    cc = CourseClassFactory(course=course)
    assert len(get_teacher_classes(t)) == 1


@pytest.mark.django_db
def test_get_classes_should_not_return_duplicate_classes():
    branch1, branch2 = BranchFactory.create_batch(2)
    course = CourseFactory(main_branch=branch1,
                           branches=[branch1, branch2])
    assert len(course.branches.all()) == 2
    cc = CourseClassFactory(course=course)
    assert len(get_classes([branch1.pk])) == 1
    assert len(get_classes([branch2.pk])) == 1
    assert len(get_classes([branch1.pk, branch2.pk])) == 1
