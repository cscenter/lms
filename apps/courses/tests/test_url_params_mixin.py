import pytest
from django.http import Http404
from django.utils.encoding import smart_bytes

from core.tests.factories import BranchFactory
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.settings import Branches
from users.tests.factories import StudentFactory


@pytest.mark.django_db
@pytest.mark.skip("WIP CourseURLParamsMixin")
def test_course_url_params_mixin_should_not_resolve_unshared_courses(client, settings):
    """
    CourseURLParamsMixin should not resolve course absolute url if it was not
    shared with user's branch.
    """
    current_semester = SemesterFactory.create_current()
    branch_center = BranchFactory(code=Branches.SPB,
                                  site__domain=settings.TEST_DOMAIN)
    branch_club = BranchFactory(code=Branches.SPB,
                                site__domain=settings.ANOTHER_DOMAIN)
    course_center = CourseFactory(semester=current_semester,
                                  main_branch=branch_center)

    # Lookup from another branch
    s = StudentFactory(branch=branch_club)
    client.login(s)
    with pytest.raises(Http404):
        client.get(course_center.get_absolute_url())


@pytest.mark.django_db
@pytest.mark.skip("WIP CourseURLParamsMixin")
def test_course_url_params_mixin_should_not_resolve_unshared_courses(client, settings):
    """
    CourseURLParamsMixin should prioritize courses from the request.site
    if metacourse names are the same.
    """
    current_semester = SemesterFactory.create_current()
    branch_center = BranchFactory(code=Branches.SPB,
                                  site__domain=settings.TEST_DOMAIN)
    branch_club = BranchFactory(code=Branches.SPB,
                                site__domain=settings.ANOTHER_DOMAIN)
    course_center = CourseFactory(semester=current_semester,
                                  main_branch=branch_center)
    course_club = CourseFactory(semester=current_semester,
                                meta_course=course_center.meta_course,
                                main_branch=branch_club,
                                branches=[branch_center])
    assert course_center.get_absolute_url() == course_club.get_absolute_url()
    # When course2 is accessed, course1 should be opened
    response = client.get(course_club.get_absolute_url())
    assert smart_bytes(course_center.main_branch.name) in response.content
    assert smart_bytes(course_club.main_branch.name) not in response.content

    # Lookup from another branch
    s = StudentFactory(branch__code=Branches.NSK)
    client.login(s.user)
    response = client.get(course_club.get_absolute_url())
    assert smart_bytes(course_center.main_branch.name) in response.content
    assert smart_bytes(course_club.main_branch.name) not in response.content