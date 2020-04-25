import pytest
from django.core.exceptions import ValidationError

from core.tests.factories import BranchFactory
from courses.models import CourseBranch
from courses.services import CourseService
from courses.tests.factories import CourseFactory


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
