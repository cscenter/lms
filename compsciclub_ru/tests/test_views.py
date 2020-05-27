from functools import partial

import pytest
from bs4 import BeautifulSoup
from django.contrib.sites.models import Site
from django.utils.encoding import smart_bytes

from compsciclub_ru.views import ClubClassesFeed
from core.middleware import BranchViewMiddleware
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.tests.factories import CourseClassFactory, SemesterFactory, CourseFactory
from learning.settings import Branches
from users.tests.factories import TeacherFactory


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
                                          main_branch=branch_spb_center)
    course_center_public = CourseFactory(semester=current_semester,
                                         main_branch=branch_spb_center)
    course_center_outdated = CourseFactory(semester=previous_semester,
                                           main_branch=branch_spb_center)
    course_club_actual = CourseFactory(semester=current_semester)
    course_club_outdated = CourseFactory(semester=previous_semester)

    # Some of CS Courses were shared with CS Club
    course_center_public.branches.add(branch_spb_club)
    course_center_outdated.branches.add(branch_spb_club)

    response = client.get(reverse('index'))
    assert response.status_code == 200
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
                                          main_branch=branch_spb_center)
    course_center_public = CourseFactory(semester=current_semester,
                                         main_branch=branch_spb_center)
    course_club_kzn_shared = CourseFactory(semester=current_semester,
                                           main_branch__code="kzn")

    # Courses were shared with CS Club
    course_center_public.branches.add(branch_spb_club)
    course_club_kzn_shared.branches.add(branch_spb_club)

    response = client.get(reverse('course_list'))
    assert response.status_code == 200
    assert smart_bytes(course_center_private.meta_course.name) not in response.content
    assert smart_bytes(course_center_public.meta_course.name) in response.content
    assert smart_bytes(course_club_kzn_shared.meta_course.name) in response.content


@pytest.mark.django_db
def test_club_classes_feed(rf, client, settings, mocker):
    """
    Сlub students should only see classes from any courses that:
      * are hosted by the current club branch
      * were shared with the current club branch
    """
    current_semester = SemesterFactory.create_current()
    branch_center = BranchFactory(code=Branches.SPB,
                                  site__domain=settings.ANOTHER_DOMAIN)
    branch_club = BranchFactory(code=Branches.SPB)
    co_center = CourseFactory.create(semester=current_semester,
                                     main_branch=branch_center)
    co_spb = CourseFactory.create(semester=current_semester)
    co_kzn = CourseFactory.create(semester=current_semester,
                                  main_branch__code="kzn")
    cc_center = CourseClassFactory(course=co_center)
    cc_spb = CourseClassFactory(course=co_spb)
    cc_kzn = CourseClassFactory(course=co_kzn)

    # Create mock request for ClubClassesFeed, url does not matter, only branch is used
    request = rf.request()
    request.site = Site.objects.get(id=settings.SITE_ID)
    middleware = BranchViewMiddleware(mocker.stub(name='get_response'))
    process_view = partial(middleware.process_view, view_func=lambda: "",
                           view_args=[])
    process_view(request, view_kwargs={"branch_code_request": branch_club.code,
                                       "branch_trailing_slash": "/"})
    assert request.branch == branch_club
    feed = ClubClassesFeed()

    classes = list(feed.items(request))
    assert len(classes) == 1
    assert cc_center not in classes
    assert cc_spb in classes
    assert cc_kzn not in classes

    # Share center course with the club branch
    co_center.branches.add(branch_club)
    classes = list(feed.items(request))
    assert len(classes) == 2
    assert cc_center in classes


@pytest.mark.django_db
def test_teachers_list_view_should_show_only_club_course_teachers(client, settings):
    branch_spb_center = BranchFactory(code=Branches.SPB,
                                      site__domain=settings.ANOTHER_DOMAIN)
    branch_spb_club = BranchFactory(code=Branches.SPB,
                                    site__domain=settings.TEST_DOMAIN)
    t1, t2 = TeacherFactory.create_batch(2)

    # Both courses are available for club students, but only t2 should be listed among teachers
    course_center = CourseFactory(main_branch=branch_spb_center,
                                  branches=[branch_spb_club],
                                  teachers=[t1])
    course_club = CourseFactory(main_branch=branch_spb_club,
                                teachers=[t2])

    response = client.get(reverse('teachers'))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True)]
    assert t1.teacher_profile_url() not in links
    assert t2.teacher_profile_url() in links


@pytest.mark.django_db
def test_teachers_detail_view_should_show_only_club_courses(client, settings):
    branch_spb_center = BranchFactory(code=Branches.SPB,
                                      site__domain=settings.ANOTHER_DOMAIN)
    branch_spb_club = BranchFactory(code=Branches.SPB,
                                    site__domain=settings.TEST_DOMAIN)
    t = TeacherFactory()

    # Both courses are available for club students, but only course_club should be listed among teacher courses
    course_center = CourseFactory(main_branch=branch_spb_center,
                                  branches=[branch_spb_club],
                                  teachers=[t])
    course_club = CourseFactory(main_branch=branch_spb_club,
                                teachers=[t])

    response = client.get(reverse('teacher_detail', args=[t.pk]))
    assert response.status_code == 200
    assert smart_bytes(course_center.meta_course.name) not in response.content
    assert smart_bytes(course_club.meta_course.name) in response.content
