# -*- coding: utf-8 -*-
import datetime

import pytest
from django.conf import settings
from django.utils.encoding import smart_bytes

from core.timezone import now_local
from core.urls import reverse
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.models import Enrollment
from users.tests.factories import StudentFactory


@pytest.mark.django_db
@pytest.mark.skip
def test_courses_list(client):
    """Сlub students can't see center courses"""
    current_semester = SemesterFactory.create_current()
    co_center = CourseFactory(semester=current_semester,
                              is_open=False,
                              city=settings.DEFAULT_CITY_CODE)
    co_spb = CourseFactory(semester=current_semester,
                           is_open=True,
                           city=settings.DEFAULT_CITY_CODE)
    co_kzn = CourseFactory.create(semester=current_semester,
                                  city="kzn")
    response = client.get(reverse('course_list'))
    assert smart_bytes(co_center.meta_course.name) not in response.content
    assert smart_bytes(co_spb.meta_course.name) in response.content
    assert smart_bytes(co_kzn.meta_course.name) not in response.content


@pytest.mark.django_db
def test_enrollment(client, settings):
    """ Club Student can enroll only on open courses """
    # settings.SITE_ID = settings.CLUB_SITE_ID
    tomorrow = now_local('spb') + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(city_code='spb',
                                          enrollment_end_at=tomorrow.date())
    co = CourseFactory(city='spb', semester=term, is_open=False)
    assert co.enrollment_is_open
    student_center = StudentFactory(
        required_groups__site_id=settings.CENTER_SITE_ID,
        city_id='spb')
    student_club = StudentFactory(
        required_groups__site_id=settings.CLUB_SITE_ID,
        city_id='spb')
    form = {'course_pk': co.pk}
    client.login(student_center)
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_club)
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
