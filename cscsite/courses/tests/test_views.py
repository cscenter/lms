import datetime
from typing import Optional

import pytest
import pytz
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import model_to_dict
from django.utils import formats

from courses.factories import CourseFactory, CourseNewsFactory, \
    AssignmentFactory, CourseClassFactory, CourseTeacherFactory
from learning.settings import AcademicRoles
from users.factories import TeacherCenterFactory


def get_timezone_gmt_offset(tz: pytz.timezone) -> Optional[datetime.timedelta]:
    return tz.localize(datetime.datetime(2017, 1, 1)).utcoffset()


SPB_OFFSET = get_timezone_gmt_offset(settings.TIME_ZONES['spb'])
NSK_OFFSET = get_timezone_gmt_offset(settings.TIME_ZONES['nsk'])


@pytest.mark.django_db
def test_course_news(settings, admin_client):
    settings.LANGUAGE_CODE = 'ru'
    news = CourseNewsFactory(
        course__city_id='spb',
        created=datetime.datetime(2017, 1, 13, 20, 0, 0, 0,
                                  tzinfo=pytz.UTC))
    co = news.course
    date_in_utc = news.created
    localized = date_in_utc.astimezone(settings.TIME_ZONES['spb'])
    assert localized.utcoffset() == datetime.timedelta(
        seconds=SPB_OFFSET.total_seconds())
    assert localized.hour == 23
    date_str = "{:02d}".format(localized.day)
    assert date_str == "13"
    response = admin_client.get(co.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(date_str in s.string for s in
               html.find_all('div', {"class": "date"}))
    # For NSK we should live in the next day
    co.city_id = 'nsk'
    co.save()
    localized = date_in_utc.astimezone(settings.TIME_ZONES['nsk'])
    assert localized.utcoffset() == datetime.timedelta(
        seconds=NSK_OFFSET.total_seconds())
    assert localized.hour == 3
    assert localized.day == 14
    date_str = "{:02d}".format(localized.day)
    assert date_str == "14"
    response = admin_client.get(co.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(date_str in s.string for s in
               html.find_all('div', {"class": "date"}))


@pytest.mark.django_db
def test_course_assignment_deadline_l10n(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    teacher = TeacherCenterFactory()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course__city_id='spb',
                                   course__teachers=[teacher])
    co = assignment.course
    client.login(teacher)
    response = client.get(co.get_url_for_tab('assignments'))
    html = BeautifulSoup(response.content, "html.parser")
    deadline_date_str = formats.date_format(assignment.deadline_at_local(), 'd E')
    assert deadline_date_str == "01 января"
    assert any(deadline_date_str in s.text for s in
               html.find_all('div', {"class": "assignment-deadline"}))
    deadline_time_str = formats.date_format(assignment.deadline_at_local(), 'H:i')
    assert deadline_time_str == "18:00"
    assert any(deadline_time_str in s.string for s in
               html.find_all('span', {"class": "text-muted"}))


@pytest.mark.django_db
def test_update_derivable_fields(curator, client, mocker):
    """Derivable fields should be recalculated on updating course class"""
    mocker.patch("courses.tasks.maybe_upload_slides_yandex.delay")
    teacher = TeacherCenterFactory()
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher])
    cc1 = CourseClassFactory.create(course=co, video_url="")
    co.refresh_from_db()
    assert not co.materials_video
    assert not co.materials_slides
    assert not co.materials_files
    slides_file = SimpleUploadedFile("slides.pdf", b"slides_content")
    client.login(curator)
    form = model_to_dict(cc1)
    form['slides'] = slides_file
    client.post(cc1.get_update_url(), form)
    co.refresh_from_db()
    assert not co.materials_video
    assert co.materials_slides
    assert not co.materials_files
    cc2 = CourseClassFactory.create(course=co, video_url="youtuuube")
    co.refresh_from_db()
    assert co.materials_video
    # Slides were uploaded on first class
    assert co.materials_slides
    assert not co.materials_files


@pytest.mark.django_db
def test_course_assignment_timezone(settings, client):
    """
    Teacher of the course always must see timezone of course offering,
    even if he is also learning in CS Center.
    """
    teacher_nsk = TeacherCenterFactory(city_id='nsk')
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(2017, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course__city_id='spb',
                                   course__is_correspondence=True)
    co = assignment.course
    client.login(teacher_nsk)
    url = co.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    teacher_nsk.groups.add(AcademicRoles.STUDENT_CENTER)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    # Don't override timezone if current authenticated user is actual teacher of
    # the course
    CourseTeacherFactory(course=co, teacher=teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None