import pytest
from dateutil.relativedelta import relativedelta

from auth.mixins import PermissionRequiredMixin
from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from courses.calendar import MonthFullWeeksEventsCalendar, WeekEventsCalendar
from courses.tests.factories import CourseClassFactory, CourseFactory
from learning.settings import Branches
from learning.tests.factories import EnrollmentFactory, GraduateFactory
from learning.tests.utils import flatten_calendar_month_events
from users.tests.factories import (
    CuratorFactory, StudentFactory, StudentProfileFactory, TeacherFactory,
    VolunteerFactory
)


def flatten_events(calendar: WeekEventsCalendar):
    return [calendar_event for day in calendar.days()
            for calendar_event in day.events]


@pytest.mark.django_db
def test_teacher_timetable_security(curator, client, assert_login_redirect):
    allowed = [CuratorFactory, TeacherFactory]
    timetable_url = reverse('teaching:timetable')
    for factory_class in allowed:
        user = factory_class()
        client.login(user)
        response = client.get(timetable_url)
        assert response.status_code == 200
        client.logout()
    denied = [StudentFactory, GraduateFactory, VolunteerFactory]
    for factory_class in denied:
        user = factory_class()
        client.login(user)
        assert_login_redirect(timetable_url, method='get')
        client.logout()


@pytest.mark.django_db
def test_teacher_timetable(client):
    teacher = TeacherFactory()
    client.login(teacher)
    timetable_url = reverse('teaching:timetable')
    response = client.get(timetable_url)
    assert response.status_code == 200
    events = flatten_events(response.context_data['calendar'])
    assert len(events) == 0
    branch_spb = BranchFactory(code=Branches.SPB)
    today_spb = now_local(branch_spb.get_timezone()).date()
    CourseClassFactory.create_batch(3, course__teachers=[teacher],
                                    date=today_spb)
    response = client.get(timetable_url)
    calendar = response.context_data['calendar']
    assert isinstance(calendar, MonthFullWeeksEventsCalendar)
    assert len(flatten_calendar_month_events(calendar)) == 3
    next_month_qstr = ("?year={0}&month={1}"
                       .format(calendar.next_month.year,
                               calendar.next_month.month))
    next_month_url = timetable_url + next_month_qstr
    assert next_month_qstr.encode() in response.content
    response = client.get(next_month_url)
    assert response.status_code == 200
    calendar = response.context_data['calendar']
    days = calendar.days()
    expected = 0
    if days:
        first_day, last_day = days[0].date, days[-1].date
        if first_day <= today_spb <= last_day:
            expected = 3
    assert len(flatten_calendar_month_events(calendar)) == expected
    next_month_date = today_spb + relativedelta(months=1)
    CourseClassFactory.create_batch(2, course__teachers=[teacher],
                                    date=next_month_date)
    response = client.get(next_month_url)
    calendar = response.context_data['calendar']
    assert len(flatten_calendar_month_events(calendar)) == 2 + expected


@pytest.mark.django_db
def test_student_timetable_view_security(client, lms_resolver):
    timetable_url = reverse('study:timetable')
    resolver = lms_resolver(timetable_url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == "study.view_schedule"


@pytest.mark.django_db
def test_student_timetable(client):
    student_profile = StudentProfileFactory()
    client.login(student_profile.user)
    co = CourseFactory(main_branch=student_profile.branch)
    e = EnrollmentFactory.create(course=co, student_profile=student_profile,
                                 student=student_profile.user)
    timetable_url = reverse('study:timetable')
    response = client.get(timetable_url)
    calendar = response.context_data['calendar']
    assert isinstance(calendar, WeekEventsCalendar)
    assert len(flatten_events(calendar)) == 0
    branch_spb = BranchFactory(code=Branches.SPB)
    today_spb = now_local(branch_spb.get_timezone()).date()
    CourseClassFactory.create_batch(3, course=co, date=today_spb)
    response = client.get(timetable_url)
    calendar = response.context_data['calendar']
    assert len(flatten_events(calendar)) == 3
    next_week_qstr = ("?year={0}&week={1}"
                      .format(calendar.next_week.year,
                              calendar.next_week.week))
    assert next_week_qstr.encode() in response.content
    next_week_url = timetable_url + next_week_qstr
    response = client.get(next_week_url)
    calendar = response.context_data['calendar']
    assert len(flatten_events(calendar)) == 0
    next_week_date = today_spb + relativedelta(weeks=1)
    CourseClassFactory.create_batch(2, course=co, date=next_week_date)
    response = client.get(next_week_url)
    calendar = response.context_data['calendar']
    assert len(flatten_events(calendar)) == 2
