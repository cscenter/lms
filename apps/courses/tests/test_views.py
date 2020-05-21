import datetime
from typing import Optional

import pytest
import pytz
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import model_to_dict
from django.utils import formats

from core.models import Branch
from core.tests.factories import LocationFactory, BranchFactory
from core.urls import reverse
from courses.services import CourseService
from courses.tests.factories import CourseFactory, CourseNewsFactory, \
    AssignmentFactory, CourseClassFactory, CourseTeacherFactory
from learning.settings import Branches
from users.constants import Roles
from users.tests.factories import TeacherFactory, CuratorFactory, UserFactory


def get_timezone_gmt_offset(tz: pytz.timezone) -> Optional[datetime.timedelta]:
    return tz.localize(datetime.datetime(2017, 1, 1)).utcoffset()


@pytest.mark.django_db
def test_teacher_detail_view(client):
    user = UserFactory()
    response = client.get(user.teacher_profile_url())
    assert response.status_code == 404
    user.add_group(Roles.TEACHER)
    user.save()
    response = client.get(user.teacher_profile_url())
    assert response.status_code == 200
    assert response.context_data['teacher'] == user


@pytest.mark.django_db
def test_course_news(settings, client):
    settings.LANGUAGE_CODE = 'ru'
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    spb_offset = get_timezone_gmt_offset(branch_spb.get_timezone())
    nsk_offset = get_timezone_gmt_offset(branch_nsk.get_timezone())
    curator = CuratorFactory()
    client.login(curator)
    course = CourseFactory(main_branch=branch_spb)
    created_utc = datetime.datetime(2017, 1, 13, 20, 0, 0, 0, tzinfo=pytz.UTC)
    news = CourseNewsFactory(course=course, created=created_utc)
    created_local = created_utc.astimezone(branch_spb.get_timezone())
    assert created_local.utcoffset() == datetime.timedelta(
        seconds=spb_offset.total_seconds())
    assert created_local.hour == 23
    date_str = "{:02d}".format(created_local.day)
    assert date_str == "13"
    response = client.get(course.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(date_str in s.string for s in
               html.find_all('div', {"class": "date"}))
    # In NSK we live in the next day
    course.main_branch = Branch.objects.get_by_natural_key(Branches.NSK,
                                                           settings.SITE_ID)
    course.save()
    CourseService.sync_branches(course)
    created_local = created_utc.astimezone(branch_nsk.get_timezone())
    assert created_local.utcoffset() == datetime.timedelta(
        seconds=nsk_offset.total_seconds())
    assert created_local.hour == 3
    assert created_local.day == 14
    date_str = "{:02d}".format(created_local.day)
    assert date_str == "14"
    response = client.get(course.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(date_str in s.string for s in
               html.find_all('div', {"class": "date"}))


@pytest.mark.django_db
def test_course_assignment_deadline_l10n(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    teacher = TeacherFactory()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course__main_branch__code=Branches.SPB,
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
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    cc1 = CourseClassFactory.create(course=co, video_url="")
    co.refresh_from_db()
    assert not co.public_videos_count
    assert not co.public_slides_count
    assert not co.public_attachments_count
    slides_file = SimpleUploadedFile("slides.pdf", b"slides_content")
    client.login(curator)
    form = model_to_dict(cc1)
    form['slides'] = slides_file
    client.post(cc1.get_update_url(), form)
    co.refresh_from_db()
    assert not co.public_videos_count
    assert co.public_slides_count
    assert not co.public_attachments_count
    cc2 = CourseClassFactory(course=co, video_url="youtuuube")
    co.refresh_from_db()
    assert co.public_videos_count
    # Slides were uploaded on first class
    assert co.public_slides_count
    assert not co.public_attachments_count


@pytest.mark.django_db
def test_course_assignment_timezone(settings, client):
    """
    Course teacher always must see assignments in the timezone of the course
    """
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    # 12 january 2017 23:59 (time in UTC)
    deadline_at = datetime.datetime(2017, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    course_spb = CourseFactory(main_branch=branch_spb, branches=[branch_nsk])
    assignment = AssignmentFactory(deadline_at=deadline_at, course=course_spb)
    assignments_tab_url = course_spb.get_url_for_tab("assignments")
    teacher_nsk = TeacherFactory(branch=branch_nsk)
    client.login(teacher_nsk)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context["tz_override"] == branch_nsk.get_timezone()
    teacher_nsk.add_group(Roles.STUDENT)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context["tz_override"] == branch_nsk.get_timezone()
    # Don't override timezone if current authenticated user is an actual
    # teacher of the course
    CourseTeacherFactory(course=course_spb, teacher=teacher_nsk)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None


@pytest.mark.django_db
def test_venue_list(client):
    v = LocationFactory(city__code=settings.DEFAULT_CITY_CODE)
    response = client.get(reverse('courses:venue_list'))
    assert response.status_code == 200
    assert v in list(response.context_data['object_list'])
