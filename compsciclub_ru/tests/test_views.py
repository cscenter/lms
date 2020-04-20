import pytest
from django.utils.encoding import smart_bytes

from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.settings import Branches


@pytest.mark.django_db
def test_index_view_course_list(client, settings):
    """
    Only courses that were shared with CS Club in the current semester should be shown on the index page
    """
    current_semester = SemesterFactory.create_current()
    previous_semester = SemesterFactory.create_prev(current_semester)

    branch_spb_center = BranchFactory(code=Branches.SPB,
                                      site__domain=settings.ANOTHER_DOMAIN)
    branch_spb_club = BranchFactory(code=Branches.SPB,
                                    site__domain=settings.TEST_DOMAIN)

    course_center_private = CourseFactory(semester=current_semester,
                                          branch=branch_spb_center)
    course_center_public = CourseFactory(semester=current_semester,
                                         branch=branch_spb_center)
    course_center_outdated = CourseFactory(semester=previous_semester,
                                         branch=branch_spb_center)
    course_club_actual = CourseFactory(semester=current_semester)
    course_club_outdated = CourseFactory(semester=previous_semester)

    # Some of CS Courses were shared with CS Club
    course_center_public.additional_branches.add(branch_spb_club)
    course_center_outdated.additional_branches.add(branch_spb_club)

    response = client.get(reverse('index'))
    assert smart_bytes(course_center_private.meta_course.name) not in response.content
    assert smart_bytes(course_center_public.meta_course.name) in response.content
    assert smart_bytes(course_center_outdated.meta_course.name) not in response.content
    assert smart_bytes(course_club_actual.meta_course.name) in response.content
    assert smart_bytes(course_club_outdated.meta_course.name) not in response.content


@pytest.mark.django_db
def test_course_list(client, settings):
    """
    Сlub students can see all Club or CS Center courses that have been shared with their branch
    """
    current_semester = SemesterFactory.create_current()
    branch_spb_center = BranchFactory(code=Branches.SPB,
                                      site__domain=settings.ANOTHER_DOMAIN)
    branch_spb_club = BranchFactory(code=Branches.SPB,
                                    site__domain=settings.TEST_DOMAIN)
    course_center_private = CourseFactory(semester=current_semester,
                                          branch=branch_spb_center)
    course_center_public = CourseFactory(semester=current_semester,
                                         branch=branch_spb_center)
    course_club_kzn_shared = CourseFactory(semester=current_semester,
                                           main_branch__code="kzn")

    # Courses were shared with CS Club
    course_center_public.additional_branches.add(branch_spb_club)
    course_club_kzn_shared.additional_branches.add(branch_spb_club)
    response = client.get(reverse('course_list'))
    assert smart_bytes(course_center_private.meta_course.name) not in response.content
    assert smart_bytes(course_center_public.meta_course.name) in response.content
    assert smart_bytes(course_club_kzn_shared.meta_course.name) in response.content