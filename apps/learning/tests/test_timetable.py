import pytest
from dateutil.relativedelta import relativedelta
from django.urls import reverse

from core.timezone import now_local
from courses.calendar import WeekEventsCalendar, MonthEventsCalendar
from courses.factories import CourseClassFactory, CourseFactory
from learning.tests.factories import EnrollmentFactory
from learning.tests.utils import flatten_calendar_month_events
from users.factories import TeacherCenterFactory, StudentCenterFactory, \
    CuratorFactory, GraduateFactory, VolunteerFactory


def flatten_events(calendar: WeekEventsCalendar):
    return [calendar_event.event for day in calendar.days()
            for calendar_event in day.events]


@pytest.mark.django_db
def test_teacher_timetable_security(curator, client, assert_login_redirect):
    allowed = [CuratorFactory, TeacherCenterFactory]
    timetable_url = reverse('timetable_teacher')
    for factory_class in allowed:
        user = factory_class(city_id='spb')
        client.login(user)
        response = client.get(timetable_url)
        assert response.status_code == 200
        client.logout()
    denied = [StudentCenterFactory, GraduateFactory, VolunteerFactory]
    for factory_class in denied:
        user = factory_class(city_id='spb')
        client.login(user)
        assert_login_redirect(timetable_url, method='get')
        client.logout()


@pytest.mark.django_db
def test_teacher_timetable(client):
    teacher = TeacherCenterFactory()
    client.login(teacher)
    timetable_url = reverse('timetable_teacher')
    response = client.get(timetable_url)
    assert response.status_code == 200
    events = flatten_events(response.context['calendar'])
    assert len(events) == 0
    today_spb = now_local('spb').date()
    CourseClassFactory.create_batch(3, course__teachers=[teacher],
                                    date=today_spb)
    response = client.get(timetable_url)
    calendar = response.context['calendar']
    assert isinstance(calendar, MonthEventsCalendar)
    assert len(flatten_calendar_month_events(calendar)) == 3
    next_month_qstr = ("?year={0}&month={1}"
                       .format(calendar.next_month.year,
                               calendar.next_month.month))
    next_month_url = timetable_url + next_month_qstr
    assert next_month_qstr.encode() in response.content
    response = client.get(next_month_url)
    calendar = response.context['calendar']
    assert len(flatten_calendar_month_events(calendar)) == 0
    next_month_date = today_spb + relativedelta(months=1)
    CourseClassFactory.create_batch(2, course__teachers=[teacher],
                                    date=next_month_date)
    response = client.get(next_month_url)
    calendar = response.context['calendar']
    assert len(flatten_calendar_month_events(calendar)) == 2


@pytest.mark.django_db
def test_student_timetable_security(client, assert_login_redirect):
    allowed = [CuratorFactory, StudentCenterFactory]
    timetable_url = reverse('timetable_student')
    for factory_class in allowed:
        user = factory_class(city_id='spb')
        client.login(user)
        response = client.get(timetable_url)
        assert response.status_code == 200
        client.logout()
    denied = [TeacherCenterFactory]
    for factory_class in denied:
        user = factory_class(city_id='spb')
        client.login(user)
        assert_login_redirect(timetable_url, method='get')
        client.logout()


@pytest.mark.django_db
def test_student_timetable(client):
    student = StudentCenterFactory()
    client.login(student)
    co = CourseFactory.create(city_id='spb')
    e = EnrollmentFactory.create(course=co, student=student)
    timetable_url = reverse('timetable_student')
    response = client.get(timetable_url)
    calendar = response.context['calendar']
    assert isinstance(calendar, WeekEventsCalendar)
    assert len(flatten_events(calendar)) == 0
    today_spb = now_local('spb').date()
    CourseClassFactory.create_batch(3, course=co, date=today_spb)
    response = client.get(timetable_url)
    calendar = response.context['calendar']
    assert len(flatten_events(calendar)) == 3
    next_week_qstr = ("?year={0}&week={1}"
                      .format(calendar.next_week.year,
                              calendar.next_week.week))
    assert next_week_qstr.encode() in response.content
    next_week_url = timetable_url + next_week_qstr
    response = client.get(next_week_url)
    calendar = response.context['calendar']
    assert len(flatten_events(calendar)) == 0
    next_week_date = today_spb + relativedelta(weeks=1)
    CourseClassFactory.create_batch(2, course=co, date=next_week_date)
    response = client.get(next_week_url)
    calendar = response.context['calendar']
    assert len(flatten_events(calendar)) == 2
