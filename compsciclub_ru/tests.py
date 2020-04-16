# -*- coding: utf-8 -*-
import datetime

import pytest
from django.utils.encoding import smart_bytes

from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.models import Enrollment
from learning.settings import Branches
from users.tests.factories import StudentFactory


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
                                           branch__code="kzn")

    # Courses were shared with CS Club
    course_center_public.additional_branches.add(branch_spb_club)
    course_club_kzn_shared.additional_branches.add(branch_spb_club)

    response = client.get(reverse('course_list'))
    assert smart_bytes(course_center_private.meta_course.name) not in response.content
    assert smart_bytes(course_center_public.meta_course.name) in response.content
    assert smart_bytes(course_club_kzn_shared.meta_course.name) in response.content


@pytest.mark.django_db
def test_enrollment(client, settings):
    """ Club Student can enroll only on open courses """
    branch_spb = BranchFactory(code=Branches.SPB,
                               site__domain=settings.TEST_DOMAIN)
    today = now_local(branch_spb.get_timezone())
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    course = CourseFactory(semester=term, is_open=False)
    assert course.enrollment_is_open
    student_center = StudentFactory(
        required_groups__site_id=settings.CENTER_SITE_ID,
        branch__code=Branches.SPB)
    student_club = StudentFactory(
        required_groups__site_id=settings.CLUB_SITE_ID,
        branch=branch_spb)
    form = {'course_pk': course.pk}
    client.login(student_center)
    response = client.post(course.get_enroll_url(), form)
    assert response.status_code == 404
    assert Enrollment.objects.count() == 0
    course.is_open = True
    course.save()
    client.login(student_club)
    response = client.post(course.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
