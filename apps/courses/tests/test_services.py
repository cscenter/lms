import pytest
from django.core.exceptions import ValidationError

from core.tests.factories import BranchFactory
from courses.models import CourseBranch
from courses.services import CourseService
from courses.tests.factories import CourseFactory, CourseClassFactory
from learning.services import get_teacher_classes, get_classes
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_get_course_sync_branches():
    course = CourseFactory()
    # Append main branch
    CourseService.sync_branches(course)
    assert CourseBranch.objects.count() == 1
    assert CourseBranch.objects.get().is_main
    CourseBranch.objects.all().delete()
    # Main course branch already exists
    cb = CourseBranch(course=course, branch=course.main_branch, is_main=True)
    cb.save()
    CourseService.sync_branches(course)
    assert CourseBranch.objects.count() == 1
    assert CourseBranch.objects.get() == cb
    cb.refresh_from_db()
    assert cb.is_main
    with pytest.raises(ValidationError):
        cb2 = CourseBranch(course=course, branch=BranchFactory(), is_main=True)
        cb2.save()


@pytest.mark.django_db
def test_get_course_sync_branches_change_main_branch():
    course = CourseFactory()
    cb1 = CourseBranch.objects.get(course=course, branch=course.main_branch)
    cb2 = CourseBranch(course=course, branch=BranchFactory(), is_main=False)
    cb2.save()
    assert CourseBranch.objects.count() == 2
    course.main_branch = cb2.branch
    course.save()
    CourseService.sync_branches(course)
    assert CourseBranch.objects.count() == 1
    assert CourseBranch.objects.get() == cb2


@pytest.mark.django_db
def test_get_teacher_classes_should_not_return_duplicate_classes(settings):
    branch1, branch2 = BranchFactory.create_batch(2)
    t = TeacherFactory(branch=branch1,
                       required_groups__site_id=settings.TEST_DOMAIN_ID)
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
    print(get_classes([branch1.pk, branch2.pk]).query)
    assert len(get_classes([branch1.pk, branch2.pk])) == 1
