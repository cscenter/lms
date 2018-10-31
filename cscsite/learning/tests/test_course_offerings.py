import datetime
import pytest
import pytz
from typing import Optional

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import model_to_dict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, formats
from django.utils.encoding import smart_bytes

from learning.factories import MetaCourseFactory, SemesterFactory, \
    CourseFactory, CourseNewsFactory, AssignmentFactory, \
    CourseOfferingTeacherFactory, CourseClassFactory, EnrollmentFactory
from learning.models import Semester, Enrollment
from learning.settings import PARTICIPANT_GROUPS
from learning.tests.mixins import MyUtilitiesMixin
from users.factories import TeacherCenterFactory, StudentCenterFactory


class SemesterListTests(MyUtilitiesMixin, TestCase):
    def cos_from_semester_list(self, lst):
        return sum([semester.courseofferings
                    for pair in lst
                    for semester in pair
                    if semester], [])

    @pytest.mark.skip(reason="Fix with empty list?")
    def test_semester_list(self):
        cos = self.cos_from_semester_list(
            self.client.get(reverse('course_list'))
            .context['semester_list'])
        self.assertEqual(0, len(cos))
        # Microoptimization: avoid creating teachers/courses
        u = TeacherCenterFactory()
        mc = MetaCourseFactory.create()
        for semester_type in ['autumn', 'spring']:
            for year in range(2012, 2015):
                s = SemesterFactory.create(type=semester_type,
                                           year=year)
                CourseFactory.create(meta_course=mc, semester=s,
                                     teachers=[u])
        s = SemesterFactory.create(type='autumn', year=2015)
        CourseFactory.create(meta_course=mc, semester=s, teachers=[u])
        resp = self.client.get(reverse('course_list'))
        self.assertEqual(4, len(resp.context['semester_list']))
        cos = self.cos_from_semester_list(resp.context['semester_list'])
        self.assertEqual(7, len(cos))


class CourseOfferingMultiSiteSecurityTests(MyUtilitiesMixin, TestCase):
    @pytest.mark.skip("Doesnt work if term is summer!")
    def test_list_center_site(self):
        """Center students can see club CO only from SPB"""
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(semester=s,
                                  city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseFactory.create(semester=s,
                                      city="kzn")
        resp = self.client.get(reverse('course_list'))
        # Really stupid test, we filter summer courses on /courses/ page
        if s.type != Semester.TYPES.summer:
            self.assertContains(resp, co.meta_course.name)
            self.assertNotContains(resp, co_kzn.meta_course.name)
        # Note: Club related tests in csclub app

    def test_student_list_center_site(self):
        student = StudentCenterFactory(city_id=settings.DEFAULT_CITY_CODE)
        self.doLogin(student)
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory.create(semester=s,
                                  city=settings.DEFAULT_CITY_CODE)
        co_kzn = CourseFactory.create(semester=s, city="kzn")
        response = self.client.get(reverse('course_list_student'))
        self.assertEqual(len(response.context['ongoing_rest']), 1)


# Test timezones


TEST_YEAR = 2017


def get_timezone_gmt_offset(tz: pytz.timezone) -> Optional[datetime.timedelta]:
    return tz.localize(datetime.datetime(TEST_YEAR, 1, 1)).utcoffset()


SPB_OFFSET = get_timezone_gmt_offset(settings.TIME_ZONES['spb'])
NSK_OFFSET = get_timezone_gmt_offset(settings.TIME_ZONES['nsk'])


@pytest.mark.django_db
def test_news_get_city_timezone(settings):
    news = CourseNewsFactory(course_offering__city_id='nsk')
    assert news.get_city_timezone() == settings.TIME_ZONES['nsk']
    news.course_offering.city_id = 'spb'
    news.course_offering.save()
    news.refresh_from_db()
    assert news.get_city_timezone() == settings.TIME_ZONES['spb']


@pytest.mark.django_db
def test_course_offering_news(settings, admin_client):
    settings.LANGUAGE_CODE = 'ru'
    news = CourseNewsFactory(course_offering__city_id='spb',
                             created=datetime.datetime(TEST_YEAR, 1, 13,
                                                               20, 0, 0, 0,
                                                               tzinfo=pytz.UTC))
    co = news.course_offering
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
def test_course_offering_assignment_deadline_l10n(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    teacher = TeacherCenterFactory()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course_offering__city_id='spb',
                                   course_offering__teachers=[teacher])
    co = assignment.course_offering
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
def test_course_offering_is_correspondence(settings, client):
    """Test how `tz_override` works with different user roles"""
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(TEST_YEAR, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course_offering__city_id='spb',
                                   course_offering__is_correspondence=False)
    teacher_nsk = TeacherCenterFactory(city_id='nsk')
    student_spb = StudentCenterFactory(city_id='spb')
    student_nsk = StudentCenterFactory(city_id='nsk')
    co = assignment.course_offering
    # Unauthenticated user doesn't see tab
    url = co.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 302
    # Any authenticated user for offline courses see timezone of the course
    for u in [student_spb, student_nsk, teacher_nsk]:
        client.login(u)
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["tz_override"] is None
    co.is_correspondence = True
    co.save()
    client.logout()
    response = client.get(co.get_absolute_url())
    assert response.status_code == 200
    # Any authenticated user (this teacher is not actual teacher of the course)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    client.login(student_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    client.login(student_spb)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['spb']
    # Actual teacher of the course
    CourseOfferingTeacherFactory(course_offering=co, teacher=teacher_nsk)
    client.login(teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None
    # Teacher without city, fallback to course offering timezone
    teacher = TeacherCenterFactory()
    assert teacher.city_id is None
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None


@pytest.mark.django_db
def test_course_offering_assignment_timezone(settings, client):
    """
    Teacher of the course always must see timezone of course offering,
    even if he is also learning in CS Center.
    """
    teacher_nsk = TeacherCenterFactory(city_id='nsk')
    # 12 january 2017 23:59 (local time)
    deadline_at = datetime.datetime(TEST_YEAR, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course_offering__city_id='spb',
                                   course_offering__is_correspondence=True)
    co = assignment.course_offering
    client.login(teacher_nsk)
    url = co.get_url_for_tab("assignments")
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    teacher_nsk.groups.add(PARTICIPANT_GROUPS.STUDENT_CENTER)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] == settings.TIME_ZONES['nsk']
    # Don't override timezone if current authenticated user is actual teacher of
    # the course
    CourseOfferingTeacherFactory(course_offering=co, teacher=teacher_nsk)
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["tz_override"] is None


@pytest.mark.django_db
def test_update_composite_fields(curator, client, mocker):
    mocker.patch("learning.tasks.maybe_upload_slides_yandex.delay")
    teacher = TeacherCenterFactory()
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher])
    cc1 = CourseClassFactory.create(course_offering=co, video_url="")
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
    cc2 = CourseClassFactory.create(course_offering=co, video_url="youtuuube")
    co.refresh_from_db()
    assert co.materials_video
    # Slides were uploaded on first class
    assert co.materials_slides
    assert not co.materials_files


# TODO: тест для видимости таб из под разных ролей. (прятать табу во вьюхе, если нет содержимого)

# FIXME: эти тесты надо добавить на уровне модели после переноса can_view_* в permissions.py
@pytest.mark.django_db
def test_course_offering_news_tab_permissions(client):
    current_semester = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_semester)
    news = CourseNewsFactory(course_offering__city_id='spb',
                             course_offering__semester=current_semester)
    co = news.course_offering
    news_prev = CourseNewsFactory(course_offering__city_id='spb',
                                  course_offering__meta_course=co.meta_course,
                                  course_offering__semester=prev_term)
    co_prev = news_prev.course_offering
    response = client.get(co.get_absolute_url())
    assert "news" not in response.context['tabs']
    # By default student can't see the news until enroll in the course
    student_spb = StudentCenterFactory(city_id='spb')
    client.login(student_spb)
    response = client.get(co.get_absolute_url())
    assert "news" not in response.context['tabs']
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['tabs']
    e_current = EnrollmentFactory(course_offering=co, student=student_spb)
    response = client.get(co.get_absolute_url())
    assert "news" in response.context['tabs']
    # Prev courses should be successfully passed to see the news
    e_prev = EnrollmentFactory(course_offering=co_prev, student=student_spb)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['tabs']
    e_prev.grade = Enrollment.GRADES.good
    e_prev.save()
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context['tabs']
    # Teacher from the same course can view news from other offerings
    teacher = TeacherCenterFactory()
    client.login(teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['tabs']
    response = client.get(co.get_absolute_url())
    assert "news" not in response.context['tabs']
    CourseOfferingTeacherFactory(course_offering=co_prev, teacher=teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context['tabs']
    response = client.get(co.get_absolute_url())
    assert "news" in response.context['tabs']
    co_other = CourseFactory(semester=current_semester)
    response = client.get(co_other.get_absolute_url())
    assert "news" not in response.context['tabs']


@pytest.mark.django_db
def test_course_offering_assignments_tab_permissions(client):
    current_semester = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_semester)
    meta_course = MetaCourseFactory()
    a = AssignmentFactory(course_offering__semester=prev_term,
                          course_offering__meta_course=meta_course)
    co_prev = a.course_offering
    co = CourseFactory(meta_course=meta_course,
                       semester=current_semester)
    teacher = TeacherCenterFactory()
    CourseOfferingTeacherFactory(teacher=teacher, course_offering=co)
    # Unauthenticated user can't see tab at all
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" not in response.context['tabs']
    # Teacher can see links to assignments from other course sessions
    client.login(teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" in response.context['tabs']
    assert smart_bytes(a.get_teacher_url()) in response.content
    student = StudentCenterFactory()
    client.login(student)
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" in response.context['tabs']
    assert len(response.context['tabs']['assignments'].context) == 1
    assert smart_bytes(a.get_teacher_url()) not in response.content
