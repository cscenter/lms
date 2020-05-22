"""
This module contains tests for CourseURLParamsMixin, which resolves URL for pages related to a certain course.
Course lookup is trivial in case when all MetaCourse names are unique for a certain semester, only special cases
are covered. Only CourseDetailView pages are tested.
"""
import pytest
from bs4 import BeautifulSoup
from django.contrib.sites.models import Site
from django.utils.encoding import smart_bytes

from core.tests.factories import BranchFactory
from courses.tests.factories import SemesterFactory, CourseFactory, MetaCourseFactory
from learning.settings import Branches
from users.tests.factories import StudentFactory


def get_branch_from_course_detail_view(response):
    soup = BeautifulSoup(response.content, 'html.parser')
    branch_container = soup.select('h2.course-main-title > small')
    assert len(branch_container) == 1
    return branch_container[0].text


@pytest.mark.django_db
def test_should_not_resolve_courses_that_do_not_exist(client):
    course_in_db = CourseFactory(main_branch__code=Branches.SPB)
    s = StudentFactory(branch__code=Branches.SPB)
    client.login(s)
    response = client.get(course_in_db.get_absolute_url())
    assert response.status_code == 200

    course_not_in_db = CourseFactory.build(main_branch__code=Branches.NSK)
    response = client.get(course_not_in_db.get_absolute_url())
    assert response.status_code == 404


@pytest.mark.django_db
def test_should_resolve_courses_from_different_branches_of_same_site(client, settings):
    """
    Checks that all courses with the same name from different branches are correctly resolved on one site.
    """
    branch_spb = BranchFactory(code=Branches.SPB,
                               site__domain=settings.TEST_DOMAIN)
    branch_nsk = BranchFactory(code=Branches.NSK,
                               site__domain=settings.TEST_DOMAIN)
    semester = SemesterFactory.create_current()
    meta_course = MetaCourseFactory()
    course_spb = CourseFactory(meta_course=meta_course,
                               main_branch=branch_spb,
                               semester=semester)
    course_nsk = CourseFactory(meta_course=meta_course,
                               main_branch=branch_nsk,
                               semester=semester)

    s = StudentFactory(branch=branch_spb)
    client.login(s)
    response = client.get(course_spb.get_absolute_url())
    assert response.status_code == 200
    assert branch_spb.name in get_branch_from_course_detail_view(response)
    assert response.status_code == 200
    response = client.get(course_nsk.get_absolute_url())
    assert branch_nsk.name in get_branch_from_course_detail_view(response)


@pytest.mark.django_db
def test_should_not_resolve_unshared_courses_from_another_site(client, settings):
    """
    CourseURLParamsMixin should not resolve absolute url of the course from another site if it was not
    shared with user's branch.
    """
    branch_center = BranchFactory(code=Branches.SPB,
                                  site__domain=settings.TEST_DOMAIN)
    branch_other = BranchFactory(code=Branches.SPB,
                                 site__domain=settings.ANOTHER_DOMAIN)
    course_other = CourseFactory(main_branch=branch_other)

    s = StudentFactory(branch=branch_center)
    client.login(s)
    response = client.get(course_other.get_absolute_url())
    assert response.status_code == 404


@pytest.mark.django_db
def test_should_resolve_courses_with_the_same_branch_code_from_different_sites_into_one(client, settings):
    """
    When two courses with the same name and branch node are available in a certain branch,
    prioritize course from the request.site.

    In this case courses have the same URL in current implementation, so we cannot show both of them at the
    moment. Hopefully, we won't need to show both of them.
    """
    branch_spb = BranchFactory(code=Branches.SPB,
                               site__domain=settings.TEST_DOMAIN)
    branch_nsk = BranchFactory(code=Branches.NSK,
                               site__domain=settings.TEST_DOMAIN)
    branch_other = BranchFactory(code=Branches.SPB,
                                 site__domain=settings.ANOTHER_DOMAIN)
    meta_course = MetaCourseFactory()
    current_semester = SemesterFactory.create_current()
    course_spb = CourseFactory(semester=current_semester,
                               description="spb course",
                               meta_course=meta_course,
                               main_branch=branch_spb)
    course_other = CourseFactory(semester=current_semester,
                                 meta_course=meta_course,
                                 description="other course shared with spb",
                                 main_branch=branch_other,
                                 branches=[branch_spb])

    s = StudentFactory(branch=branch_spb)
    client.login(s)
    assert course_spb.get_absolute_url() == course_other.get_absolute_url()
    response = client.get(course_other.get_absolute_url())
    assert response.status_code == 200
    assert smart_bytes(course_spb.description) in response.content
    assert smart_bytes(course_other.description) not in response.content

    # Same behaviour for lookup from another branch of current site
    s = StudentFactory(branch=branch_nsk)
    client.login(s)
    assert course_spb.get_absolute_url() == course_other.get_absolute_url()
    response = client.get(course_other.get_absolute_url())
    assert response.status_code == 200
    assert smart_bytes(course_spb.description) in response.content
    assert smart_bytes(course_other.description) not in response.content


@pytest.mark.django_db
def test_should_resolve_courses_with_different_branch_codes_from_different_sites(client, settings):
    """
    If both the site and the branch code of courses are different, we can show both of them.
    """
    branch_spb = BranchFactory(code=Branches.SPB,
                               site__domain=settings.TEST_DOMAIN)
    branch_nsk = BranchFactory(code=Branches.NSK,
                               site__domain=settings.ANOTHER_DOMAIN)
    meta_course = MetaCourseFactory()
    current_semester = SemesterFactory.create_current()
    course_spb = CourseFactory(semester=current_semester,
                               meta_course=meta_course,
                               main_branch=branch_spb)
    course_nsk = CourseFactory(semester=current_semester,
                               meta_course=meta_course,
                               main_branch=branch_nsk,
                               branches=[branch_spb])

    s = StudentFactory(branch=branch_spb)
    client.login(s)
    assert course_spb.get_absolute_url() != course_nsk.get_absolute_url()
    response = client.get(course_spb.get_absolute_url())
    assert response.status_code == 200
    assert branch_spb.name in get_branch_from_course_detail_view(response)
    response = client.get(course_nsk.get_absolute_url())
    assert response.status_code == 200
    print(get_branch_from_course_detail_view(response))
    assert branch_nsk.name in get_branch_from_course_detail_view(response)


@pytest.mark.django_db
def test_should_return_stably_if_impossible_to_resolve(client, settings):
    """
    If two courses from different sites are available on the third site, there is no criteria to prefer
    one course over another, but they still can have the same URL.

    Al least we need to show something stable - currently the course that was created earlier.
    """
    third_site = Site(id=3, domain='shad.ru', name='shad.ru')
    third_site.save()
    branch_center = BranchFactory(code=Branches.SPB,
                                  site__domain=settings.TEST_DOMAIN)
    branch_club = BranchFactory(code=Branches.SPB,
                                site__domain=settings.ANOTHER_DOMAIN)
    branch_shad = BranchFactory(code=Branches.SPB,
                                site_id=3)
    current_semester = SemesterFactory.create_current()
    meta_course = MetaCourseFactory()
    course_club = CourseFactory(semester=current_semester,
                                meta_course=meta_course,
                                main_branch=branch_club,
                                branches=[branch_center])
    course_shad = CourseFactory(semester=current_semester,
                                meta_course=meta_course,
                                main_branch=branch_shad,
                                branches=[branch_center])
    assert course_shad.pk > course_club.pk

    s = StudentFactory(branch=branch_center)
    client.login(s)
    assert course_club.get_absolute_url() == course_shad.get_absolute_url()
    response = client.get(course_shad.get_absolute_url())
    assert response.status_code == 200
    assert branch_club.name in get_branch_from_course_detail_view(response)
