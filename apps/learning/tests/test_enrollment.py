import datetime

import pytest
from bs4 import BeautifulSoup
from django.utils import timezone
from django.utils.encoding import smart_bytes
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from core.constants import DATE_FORMAT_RU
from core.timezone import now_local
from core.urls import reverse
from courses.tests.factories import SemesterFactory, CourseFactory, \
    CourseNewsFactory, \
    AssignmentFactory
from learning.models import Enrollment, StudentAssignment, \
    AssignmentNotification, CourseNewsNotification
from learning.services import EnrollmentService, CourseCapacityFull
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import StudentFactory


# TODO: Убедиться, что в *.ical они тоже не попадают (see CalendarStudentView also)
# TODO: Test volunteer can enroll!
# TODO: вызывает запись на полный курс, смотрим, что после поднятия исключения CapacityFull созданный объект Enrollment не живёт в БД, т.к. транзакция откатывается


@pytest.mark.django_db
def test_unenrollment(client, assert_redirect):
    s = StudentFactory.create(city_id='spb')
    assert s.city_id is not None
    client.login(s)
    current_semester = SemesterFactory.create_current()
    co = CourseFactory.create(semester=current_semester, city='spb')
    as_ = AssignmentFactory.create_batch(3, course=co)
    form = {'course_pk': co.pk}
    # Enrollment already closed
    today = timezone.now()
    current_semester.enrollment_end_at = (today - datetime.timedelta(days=1)).date()
    current_semester.save()
    response = client.post(co.get_enroll_url(), form)
    assert response.status_code == 403
    current_semester.enrollment_end_at = (today + datetime.timedelta(days=1)).date()
    current_semester.save()
    response = client.post(co.get_enroll_url(), form, follow=True)
    assert response.status_code == 200
    assert Enrollment.objects.count() == 1
    response = client.get(co.get_absolute_url())
    assert smart_bytes("Unenroll") in response.content
    assert smart_bytes(co) in response.content
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert not enrollment.is_deleted
    client.post(co.get_unenroll_url(), form)
    assert Enrollment.active.filter(student=s, course=co).count() == 0
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    enrollment_id = enrollment.pk
    assert enrollment.is_deleted
    # Make sure student progress won't been deleted
    a_ss = (StudentAssignment.objects.filter(student=s,
                                             assignment__course=co))
    assert len(a_ss) == 3
    # On re-enroll use old record
    client.post(co.get_enroll_url(), form)
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert enrollment.pk == enrollment_id
    assert not enrollment.is_deleted
    # Check ongoing courses on student courses page are not empty
    response = client.get(reverse("study:course_list"))
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['ongoing_enrolled']) == 1
    assert len(response.context['archive_enrolled']) == 0
    # Check `back` url on unenroll action
    url = co.get_unenroll_url() + "?back=study:course_list"
    assert_redirect(client.post(url, form),
                    reverse('study:course_list'))
    assert set(a_ss) == set(StudentAssignment.objects
                                  .filter(student=s,
                                          assignment__course=co))
    # Check courses on student courses page are empty
    response = client.get(reverse("study:course_list"))
    assert len(response.context['ongoing_rest']) == 1
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['archive_enrolled']) == 0


@pytest.mark.django_db
def test_enrollment_capacity():
    student = StudentFactory(city_id='spb')
    current_semester = SemesterFactory.create_current()
    course = CourseFactory.create(city_id='spb',
                                  semester=current_semester,
                                  capacity=1,
                                  is_open=True)
    EnrollmentFactory(course=course)
    course.refresh_from_db()
    assert course.places_left == 0
    # 1 active enrollment
    assert Enrollment.objects.count() == 1
    with pytest.raises(CourseCapacityFull):
        EnrollmentService.enroll(student, course, reason='')
    # Make sure enrollment record created by enrollment service
    # was rollbacked by transaction context manager
    assert Enrollment.objects.count() == 1


@pytest.mark.django_db
def test_enrollment_capacity_view(client):
    s = StudentFactory(city_id='spb')
    client.login(s)
    current_semester = SemesterFactory.create_current()
    course = CourseFactory.create(city_id='spb',
                                  semester=current_semester,
                                  is_open=True)
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Places available")) not in response.content
    assert smart_bytes(_("No places available")) not in response.content
    course.capacity = 1
    course.save()
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Places available")) in response.content
    form = {'course_pk': course.pk}
    client.post(course.get_enroll_url(), form)
    assert 1 == Enrollment.active.filter(student=s, course=course).count()
    # Capacity is reached
    course.refresh_from_db()
    assert course.learners_count == 1
    assert course.places_left == 0
    s2 = StudentFactory(city_id='spb')
    client.login(s2)
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("No places available")) in response.content
    # POST request should be rejected
    response = client.post(course.get_enroll_url(), form)
    assert response.status_code == 302
    # Increase capacity
    course.capacity += 1
    course.save()
    assert course.places_left == 1
    response = client.get(course.get_absolute_url())
    assert (smart_bytes(_("Places available")) + b": 1") in response.content
    # Unenroll first student, capacity should increase
    client.login(s)
    response = client.post(course.get_unenroll_url(), form)
    assert Enrollment.active.filter(course=course).count() == 0
    course.refresh_from_db()
    assert course.learners_count == 0
    response = client.get(course.get_absolute_url())
    assert (smart_bytes(_("Places available")) + b": 2") in response.content


@pytest.mark.django_db
def test_enrollment(client):
    student1, student2 = StudentFactory.create_batch(2, city_id='spb')
    client.login(student1)
    today = now_local(student1.city_code)
    current_semester = SemesterFactory.create_current()
    current_semester.enrollment_end_at = today.date()
    current_semester.save()
    co = CourseFactory.create(semester=current_semester, city_id='spb')
    url = co.get_enroll_url()
    form = {'course_pk': co.pk}
    response = client.post(url, form)
    assert response.status_code == 302
    assert 1 == Enrollment.active.filter(student=student1, course=co).count()
    as_ = AssignmentFactory.create_batch(3, course=co)
    assert set((student1.pk, a.pk) for a in as_) == set(StudentAssignment.objects
                          .filter(student=student1)
                          .values_list('student', 'assignment'))
    co_other = CourseFactory.create(semester=current_semester)
    form.update({'back': 'study:course_list'})
    url = co_other.get_enroll_url()
    response = client.post(url, form)
    assert response.status_code == 302
    assert co.enrollment_set.count() == 1
    # Try to enroll to old CO
    old_semester = SemesterFactory.create(year=2010)
    old_co = CourseFactory.create(semester=old_semester)
    form = {'course_pk': old_co.pk}
    url = old_co.get_enroll_url()
    assert client.post(url, form).status_code == 403


@pytest.mark.django_db
def test_enrollment_reason_entry(client):
    student = StudentFactory(city_id='spb')
    client.login(student)
    today = now_local(student.city_code)
    current_semester = SemesterFactory.create_current()
    current_semester.enrollment_end_at = today.date()
    current_semester.save()
    co = CourseFactory.create(semester=current_semester, city_id='spb')
    form = {'course_pk': co.pk, 'reason': 'foo'}
    client.post(co.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    date = today.strftime(DATE_FORMAT_RU)
    assert Enrollment.objects.first().reason_entry == f'{date}\nfoo\n\n'
    client.post(co.get_unenroll_url(), form)
    assert Enrollment.active.count() == 0
    assert Enrollment.objects.first().reason_entry == f'{date}\nfoo\n\n'
    # Enroll for the second time, first entry reason should be saved
    form['reason'] = 'bar'
    client.post(co.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    assert Enrollment.objects.first().reason_entry == f'{date}\nbar\n\n{date}\nfoo\n\n'


@pytest.mark.django_db
def test_enrollment_leave_reason(client):
    student = StudentFactory(city_id='spb')
    client.login(student)
    today = now_local(student.city_code)
    current_semester = SemesterFactory.create_current()
    current_semester.enrollment_end_at = today.date()
    current_semester.save()
    co = CourseFactory.create(semester=current_semester, city_id='spb')
    form = {'course_pk': co.pk}
    client.post(co.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    assert Enrollment.objects.first().reason_entry == ''
    form['reason'] = 'foo'
    client.post(co.get_unenroll_url(), form)
    assert Enrollment.active.count() == 0
    today = now().strftime(DATE_FORMAT_RU)
    e = Enrollment.objects.first()
    assert today in e.reason_leave
    assert 'foo' in e.reason_leave
    # Enroll for the second time and leave with another reason
    client.post(co.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    form['reason'] = 'bar'
    client.post(co.get_unenroll_url(), form)
    assert Enrollment.active.count() == 0
    e = Enrollment.objects.first()
    assert 'foo' in e.reason_leave
    assert 'bar' in e.reason_leave
    co_other = CourseFactory.create(semester=current_semester)
    client.post(co_other.get_enroll_url(), {})
    e_other = Enrollment.active.filter(course=co_other).first()
    assert not e_other.reason_entry
    assert not e_other.reason_leave


@pytest.mark.django_db
def test_assignments(client):
    """Create assignments for active enrollments only"""
    ss = StudentFactory.create_batch(3)
    current_semester = SemesterFactory.create_current()
    co = CourseFactory.create(semester=current_semester)
    for student in ss:
        enrollment = EnrollmentFactory.create(student=student, course=co)
    assert Enrollment.objects.count() == 3
    assert StudentAssignment.objects.count() == 0
    assignment = AssignmentFactory.create(course=co)
    assert StudentAssignment.objects.count() == 3
    enrollment.is_deleted = True
    enrollment.save()
    assignment = AssignmentFactory.create(course=co)
    assert StudentAssignment.objects.count() == 5
    assert StudentAssignment.objects.filter(student=enrollment.student,
                                            assignment=assignment).count() == 0
    # Check deadline notifications sent for active enrollments only
    AssignmentNotification.objects.all().delete()
    assignment.deadline_at = assignment.deadline_at - datetime.timedelta(days=1)
    assignment.save()
    active_students = Enrollment.active.count()
    assert active_students == 2
    assert AssignmentNotification.objects.count() == active_students
    CourseNewsNotification.objects.all().delete()
    assert CourseNewsNotification.objects.count() == 0
    CourseNewsFactory.create(course=co)
    assert CourseNewsNotification.objects.count() == active_students


@pytest.mark.django_db
def test_reenrollment(client):
    """Create assignments for student if they left the course and come back"""
    s = StudentFactory(city_id='spb')
    assignment = AssignmentFactory(course__is_open=True,
                                   course__city_id='spb')
    course = assignment.course
    e = EnrollmentFactory(student=s, course=course)
    assert not e.is_deleted
    assert StudentAssignment.objects.filter(student_id=s.pk).count() == 1
    # Deactivate student enrollment
    e.is_deleted = True
    e.save()
    assert Enrollment.active.count() == 0
    assignment2 = AssignmentFactory(course=course)
    assert StudentAssignment.objects.filter(student_id=s.pk).count() == 1
    client.login(s)
    form = {'course_pk': course.pk}
    response = client.post(course.get_enroll_url(), form, follow=True)
    assert response.status_code == 200
    e.refresh_from_db()
    assert StudentAssignment.objects.filter(student_id=s.pk).count() == 2


@pytest.mark.django_db
def test_enrollment_in_other_city(client):
    tomorrow = now_local('spb') + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    co_spb = CourseFactory(city='spb', semester=term, is_open=False)
    assert co_spb.enrollment_is_open
    student_spb = StudentFactory(city_id='spb')
    student_nsk = StudentFactory(city_id='nsk')
    form = {'course_pk': co_spb.pk}
    client.login(student_spb)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 403
    assert Enrollment.objects.count() == 1
    student = StudentFactory(city_id=None)
    client.login(student)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert response.url == '/'
    assert Enrollment.objects.count() == 1
    # Check button visibility
    Enrollment.objects.all().delete()
    client.login(student_spb)
    response = client.get(co_spb.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    buttons = (html.find("div", {"class": "o-buttons-vertical"})
               .find_all(attrs={'class': 'btn'}))
    assert any("Enroll in" in s.text for s in buttons)
    for user in [student_nsk, student]:
        client.login(user)
        response = client.get(co_spb.get_absolute_url())
        assert smart_bytes("Enroll in") not in response.content


@pytest.mark.django_db
def test_correspondence_courses(client):
    """Make sure students from any city can enroll in online course"""
    tomorrow = now_local('spb') + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(enrollment_end_at=tomorrow.date())
    co_spb = CourseFactory(city_id='spb',
                           semester=term,
                           is_open=False,
                           is_correspondence=True)
    assert co_spb.enrollment_is_open
    student_spb = StudentFactory(city_id='spb')
    student_nsk = StudentFactory(city_id='nsk')
    form = {'course_pk': co_spb.pk}
    client.login(student_spb)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(co_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 2


@pytest.mark.django_db
def test_enrollment_is_enrollment_open(client):
    today = now_local('spb')
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(city_code='spb',
                                          enrollment_end_at=today.date())
    co_spb = CourseFactory(city='spb', semester=term, is_open=False,
                           completed_at=tomorrow.date())
    assert co_spb.enrollment_is_open
    student_spb = StudentFactory(city_id='spb')
    client.login(student_spb)
    response = client.get(co_spb.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    buttons = (html.find("div", {"class": "o-buttons-vertical"})
               .find_all(attrs={'class': 'btn'}))
    assert any("Enroll in" in s.text for s in buttons)
    default_completed_at = co_spb.completed_at
    co_spb.completed_at = today.date()
    co_spb.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content
    co_spb.completed_at = default_completed_at
    co_spb.save()
    assert co_spb.enrollment_is_open
    term.enrollment_start_at = today.date()
    term.save()
    assert co_spb.enrollment_is_open
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") in response.content
    # What if enrollment not stated yet
    term.enrollment_start_at = tomorrow.date()
    term.enrollment_end_at = tomorrow.date()
    term.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content
    # Already completed
    term.enrollment_start_at = yesterday.date()
    term.enrollment_end_at = yesterday.date()
    term.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content


