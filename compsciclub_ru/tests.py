# -*- coding: utf-8 -*-
import datetime

import pytest
import pytz
from django.conf import settings
from django.utils.encoding import smart_bytes

from core.tests.utils import now_for_branch, ANOTHER_DOMAIN_ID
from core.timezone import now_local
from core.urls import reverse
from courses.models import Course
from courses.tests.factories import SemesterFactory, CourseFactory
from courses.utils import get_current_term_pair
from learning.models import Enrollment
from learning.settings import Branches
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import StudentFactory


@pytest.mark.django_db
@pytest.mark.skip
def test_courses_list(client):
    """Сlub students can't see center courses"""
    current_semester = SemesterFactory.create_current()
    co_center = CourseFactory(semester=current_semester,
                              is_open=False)
    co_spb = CourseFactory(semester=current_semester,
                           is_open=True)
    co_kzn = CourseFactory.create(semester=current_semester,
                                  city__code="kzn")
    response = client.get(reverse('course_list'))
    assert smart_bytes(co_center.meta_course.name) not in response.content
    assert smart_bytes(co_spb.meta_course.name) in response.content
    assert smart_bytes(co_kzn.meta_course.name) not in response.content


@pytest.mark.django_db
def test_enrollment(client, settings):
    """ Club Student can enroll only on open courses """
    # settings.SITE_ID = settings.CLUB_SITE_ID
    tomorrow = now_for_branch(Branches.SPB) + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    co = CourseFactory(semester=term, is_open=False)
    assert co.enrollment_is_open
    student_center = StudentFactory(
        required_groups__site_id=settings.CENTER_SITE_ID,
        branch__code=Branches.SPB)
    student_club = StudentFactory(
        required_groups__site_id=settings.CLUB_SITE_ID,
        branch__code=Branches.SPB)
    form = {'course_pk': co.pk}
    client.login(student_center)
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_club)
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.urls('compsciclub_ru.urls')
@pytest.mark.skip('Для этого теста нужно полностью подменять конфиг')
def test_student_courses_list_csclub(client, settings, mocker):
    settings.SITE_ID = settings.CLUB_SITE_ID
    settings.SUBDOMAIN_URLCONFS = {None: settings.ROOT_URLCONF}
    # Fix year and term
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    now_fixed = datetime.datetime(2016, month=3, day=8, tzinfo=pytz.utc)
    mocked_timezone.return_value = now_fixed
    now_year, now_season = get_current_term_pair()
    assert now_season == "spring"
    url = reverse('study:course_list')
    student = StudentFactory(required_groups__site_id=ANOTHER_DOMAIN_ID,
                             city_id='spb')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    # Make sure in tests we fallback to default city which is 'spb'
    assert response.context['request'].city_code == 'spb'
    # Show only open courses
    current_term = SemesterFactory.create_current(
        city_code=settings.DEFAULT_CITY_CODE)
    assert current_term.type == "spring"
    settings.SITE_ID = settings.CENTER_SITE_ID
    co = CourseFactory.create(semester__type=now_season,
                              semester__year=now_year, city_id='nsk',
                              is_open=False)
    settings.SITE_ID = settings.CLUB_SITE_ID
    # compsciclub.ru can't see center courses with default manager
    assert Course.objects.count() == 0
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['archive_enrolled']) == 0
    settings.SITE_ID = settings.CENTER_SITE_ID
    co.is_open = True
    co.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    assert Course.objects.count() == 1
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['archive_enrolled']) == 0
    co.city_id = 'spb'
    co.save()
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co}
    assert len(response.context['archive_enrolled']) == 0
    # Summer courses are hidden for compsciclub.ru
    summer_semester = SemesterFactory.create(year=now_year - 1, type='summer')
    co.semester = summer_semester
    co.save()
    settings.SITE_ID = settings.CENTER_SITE_ID
    co_active = CourseFactory.create(semester__type=now_season,
                                     semester__year=now_year,
                                     city_id='spb',
                                     is_open=True)
    settings.SITE_ID = settings.CLUB_SITE_ID
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co_active}
    assert len(response.context['archive_enrolled']) == 0
    # But student can see them in list if they already enrolled
    EnrollmentFactory.create(student=student, course=co)
    response = client.get(url)
    assert len(response.context['ongoing_rest']) == 1
    assert len(response.context['archive_enrolled']) == 1
    assert set(response.context['archive_enrolled']) == {co}