import datetime

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from core.tests.factories import LocationFactory, BranchFactory
from core.urls import reverse
from courses.tests.factories import CourseFactory, CourseClassFactory
from learning.settings import Branches
from learning.tests.factories import EventFactory, \
    EnrollmentFactory, GraduateFactory
from learning.tests.utils import flatten_calendar_month_events
from users.tests.factories import StudentFactory, TeacherFactory


# TODO: add test: kzn courses not shown on center site and spb on kzn
# TODO: add test: summer courses not shown on club site on main page
# TODO: для СПБ не показываются события НСК (наоборот будет уже верно)


@pytest.mark.django_db
def test_teacher_calendar_group_security(client, assert_login_redirect):
    url = reverse('teaching:calendar')
    assert_login_redirect(url)
    client.login(StudentFactory())
    assert_login_redirect(url)
    client.login(GraduateFactory())
    assert_login_redirect(url)
    client.login(TeacherFactory())
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_teacher_calendar(client):
    url = reverse('teaching:calendar')
    teacher_spb = TeacherFactory(branch__code=Branches.SPB)
    other_teacher = TeacherFactory(branch__code=Branches.SPB)
    client.login(teacher_spb)
    response = client.get(url)
    classes = flatten_calendar_month_events(response.context['calendar'])
    assert len(classes) == 0
    this_month_date = (datetime.datetime.now()
                       .replace(day=15, tzinfo=timezone.utc))
    own_classes = list(
        CourseClassFactory
        .create_batch(3, course__teachers=[teacher_spb],
                      date=this_month_date))
    others_classes = list(
        CourseClassFactory
        .create_batch(5, course__teachers=[other_teacher],
                      date=this_month_date))
    location = LocationFactory(city_id=teacher_spb.branch.city_id)
    events = EventFactory.create_batch(2, date=this_month_date,
                                       venue=location)
    # teacher should see only his own classes and non-course events
    resp = client.get(url)
    classes = flatten_calendar_month_events(resp.context['calendar'])
    assert set(own_classes + events) == set(classes)
    # No events on the next month
    next_month_qstr = (
        "?year={0}&month={1}"
        .format(resp.context['calendar'].next_month.year,
                str(resp.context['calendar'].next_month.month)))
    next_month_url = url + next_month_qstr
    assert smart_bytes(next_month_qstr) in resp.content
    classes = flatten_calendar_month_events(
        client.get(next_month_url).context['calendar'])
    assert classes == []
    # Add some and test
    next_month_date = this_month_date + relativedelta(months=1)
    next_month_classes = (
        CourseClassFactory
        .create_batch(2, course__teachers=[teacher_spb],
                      date=next_month_date))
    classes = flatten_calendar_month_events(
        client.get(next_month_url).context['calendar'])
    assert set(next_month_classes) == set(classes)
    # On a full calendar all classes should be shown
    response = client.get(reverse('teaching:calendar_full'))
    classes = flatten_calendar_month_events(response.context['calendar'])
    assert set(own_classes + others_classes + events) == set(classes)


@pytest.mark.django_db
def test_student_personal_calendar_view_permissions(lms_resolver):
    resolver = lms_resolver(reverse('study:calendar'))
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == "study.view_schedule"


@pytest.mark.django_db
def test_student_personal_calendar_view(client):
    calendar_url = reverse('study:calendar')
    student_spb = StudentFactory(branch__code=Branches.SPB)
    client.login(student_spb)
    course = CourseFactory()
    course_other = CourseFactory.create()
    e = EnrollmentFactory.create(course=course, student=student_spb)
    classes = flatten_calendar_month_events(
        client.get(calendar_url).context['calendar'])
    assert len(classes) == 0
    this_month_date = (datetime.datetime.now()
                       .replace(day=15,
                                tzinfo=timezone.utc))
    own_classes = CourseClassFactory.create_batch(3, course=course, date=this_month_date)
    others_classes = CourseClassFactory.create_batch(5, course=course_other, date=this_month_date)
    # student should see only his own classes
    response = client.get(calendar_url)
    classes = flatten_calendar_month_events(response.context['calendar'])
    assert set(own_classes) == set(classes)
    # but in full calendar all classes should be shown
    classes = flatten_calendar_month_events(
        client.get(reverse('study:calendar_full')).context['calendar'])
    assert set(own_classes + others_classes) == set(classes)
    next_month_qstr = (
        "?year={0}&month={1}"
            .format(response.context['calendar'].next_month.year,
                    str(response.context['calendar'].next_month.month)))
    next_month_url = calendar_url + next_month_qstr
    assert smart_bytes(next_month_qstr) in response.content
    classes = flatten_calendar_month_events(
        client.get(next_month_url).context['calendar'])
    assert len(classes) == 0
    next_month_date = this_month_date + relativedelta(months=1)
    next_month_classes = (
        CourseClassFactory
            .create_batch(2, course=course, date=next_month_date))
    classes = flatten_calendar_month_events(
        client.get(next_month_url).context['calendar'])
    assert set(next_month_classes) == set(classes)
    location = LocationFactory(city_id=student_spb.branch.city_id)
    events = EventFactory.create_batch(2, date=this_month_date, venue=location)
    response = client.get(calendar_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_full_calendar_security(client, assert_login_redirect):
    u = StudentFactory(branch__code=Branches.SPB)
    url = reverse('study:calendar_full')
    assert_login_redirect(url)
    client.login(u)
    assert client.get(url).status_code == 200
    u = TeacherFactory()
    client.login(u)
    response = client.get(reverse('teaching:calendar_full'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_correspondence_courses_in_a_full_calendar(client):
    """Make sure correspondence courses are visible in a full calendar"""
    student = StudentFactory(branch__code=Branches.SPB)
    client.login(student)
    this_month_date = datetime.datetime.utcnow()
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    course = CourseFactory(main_branch=branch_spb, branches=[branch_nsk])
    CourseClassFactory.create_batch(
            3, course=course, date=this_month_date)
    classes = flatten_calendar_month_events(
        client.get(reverse("study:calendar_full")).context['calendar'])
    assert len(classes) == 3
    teacher = TeacherFactory(branch=branch_spb)
    client.login(teacher)
    classes = flatten_calendar_month_events(
        client.get(reverse("teaching:calendar_full")).context['calendar'])
    assert len(classes) == 3
