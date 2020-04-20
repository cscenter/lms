# -*- coding: utf-8 -*-
import datetime

import pytest

from core.tests.factories import BranchFactory
from core.timezone import now_local
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.models import Enrollment
from learning.settings import Branches
from users.tests.factories import StudentFactory


@pytest.mark.django_db
def test_enrollment(client, settings):
    """ Club Student can enroll only on open courses """
    branch_spb = BranchFactory(code=Branches.SPB,
                               site__domain=settings.TEST_DOMAIN)
    today = now_local(branch_spb.get_timezone())
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    course = CourseFactory(semester=term)
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
    assert response.status_code == 403
    assert Enrollment.objects.count() == 0
    course.additional_branches.add(branch_spb)
    course.save()
    client.login(student_club)
    response = client.post(course.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
