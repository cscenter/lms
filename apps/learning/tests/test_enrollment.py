import datetime

import pytest
from bs4 import BeautifulSoup
from django.utils import timezone
from django.utils.encoding import smart_bytes
from django.utils.timezone import now
from django.utils.translation import gettext as _

from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.timezone.constants import DATE_FORMAT_RU
from core.urls import reverse, branch_aware_reverse
from courses.models import CourseBranch
from courses.tests.factories import SemesterFactory, CourseFactory, \
    AssignmentFactory
from learning.models import Enrollment, StudentAssignment, StudentGroup, \
    EnrollmentPeriod
from learning.services import EnrollmentService, CourseCapacityFull, \
    StudentGroupService, get_student_profile
from learning.settings import StudentStatuses, Branches
from learning.tests.factories import EnrollmentFactory, CourseInvitationFactory
from users.tests.factories import StudentFactory, InvitedStudentFactory


# TODO: запись кем-то без группы INVITED.
# TODO: после регистрации у чуваков есть необходимые поля и группы. Нужно ли тестить отправку email? вроде как асинхронно высылается, значит надо (мб моки уже есть в текстах клуба, хз)


# TODO: Убедиться, что в *.ical они тоже не попадают (see CalendarStudentView also)


@pytest.mark.django_db
def test_service_enroll(settings):
    student = StudentFactory()
    student2 = StudentFactory(branch=student.branch)
    current_semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student.branch, semester=current_semester)
    student_profile = student.get_student_profile(settings.SITE_ID)
    enrollment = EnrollmentService.enroll(student_profile, course, 'test enrollment')
    reason_entry = EnrollmentService._format_reason_record('test enrollment', course)
    assert enrollment.reason_entry == reason_entry
    assert not enrollment.is_deleted
    assert enrollment.student_group_id is None
    student_group = StudentGroupService.resolve(course, student2,
                                                settings.SITE_ID)
    student_profile2 = student2.get_student_profile(settings.SITE_ID)
    enrollment = EnrollmentService.enroll(student_profile2, course,
                                          'test enrollment',
                                          student_group=student_group)
    assert enrollment.student_group == student_group


@pytest.mark.django_db
def test_enrollment_capacity(settings):
    student = StudentFactory()
    current_semester = SemesterFactory.create_current()
    course = CourseFactory.create(main_branch=student.branch,
                                  semester=current_semester,
                                  capacity=1)
    EnrollmentFactory(course=course)
    course.refresh_from_db()
    assert course.places_left == 0
    # 1 active enrollment
    assert Enrollment.objects.count() == 1
    with pytest.raises(CourseCapacityFull):
        student_profile = student.get_student_profile(settings.SITE_ID)
        EnrollmentService.enroll(student_profile, course, reason_entry='')
    # Make sure enrollment record created by enrollment service
    # was rollbacked by transaction context manager
    assert Enrollment.objects.count() == 1


@pytest.mark.django_db
def test_enrollment_capacity_view(client):
    s = StudentFactory()
    client.login(s)
    future = now() + datetime.timedelta(days=2)
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date()
    )
    course = CourseFactory(main_branch=s.branch,
                           semester=current_semester,)
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Places available")) not in response.content
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
    s2 = StudentFactory(branch=course.main_branch)
    client.login(s2)
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Enroll in")) not in response.content
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
@pytest.mark.parametrize("inactive_status", StudentStatuses.inactive_statuses)
def test_enrollment_inactive_student(inactive_status, client, settings):
    student = StudentFactory(branch__code=Branches.SPB)
    client.login(student)
    tomorrow = now_local(student.get_timezone()) + datetime.timedelta(days=1)
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=tomorrow.date())
    course = CourseFactory(semester=current_semester)
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    assert smart_bytes(_("Enroll in")) in response.content
    student_profile = get_student_profile(student, settings.SITE_ID)
    student_profile.status = inactive_status
    student_profile.save()
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Enroll in")) not in response.content


@pytest.mark.django_db
def test_enrollment(client):
    student1, student2 = StudentFactory.create_batch(2)
    client.login(student1)
    today = now_local(student1.get_timezone())
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    current_semester.save()
    course = CourseFactory(main_branch=student1.branch, semester=current_semester)
    url = course.get_enroll_url()
    form = {'course_pk': course.pk}
    response = client.post(url, form)
    assert response.status_code == 302
    assert 1 == Enrollment.active.filter(student=student1, course=course).count()
    as_ = AssignmentFactory.create_batch(3, course=course)
    assert set((student1.pk, a.pk) for a in as_) == set(StudentAssignment.objects
                          .filter(student=student1)
                          .values_list('student', 'assignment'))
    co_other = CourseFactory.create(semester=current_semester)
    form.update({'back': 'study:course_list'})
    url = co_other.get_enroll_url()
    response = client.post(url, form)
    assert response.status_code == 302
    assert course.enrollment_set.count() == 1
    # Try to enroll to old CO
    old_semester = SemesterFactory.create(year=2010)
    old_co = CourseFactory.create(semester=old_semester)
    form = {'course_pk': old_co.pk}
    url = old_co.get_enroll_url()
    assert client.post(url, form).status_code == 403


@pytest.mark.django_db
def test_enrollment_reason_entry(client):
    student = StudentFactory()
    client.login(student)
    today = now_local(student.get_timezone())
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    course = CourseFactory(main_branch=student.branch, semester=current_term)
    form = {'course_pk': course.pk, 'reason': 'foo'}
    client.post(course.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    date = today.strftime(DATE_FORMAT_RU)
    assert Enrollment.objects.first().reason_entry == f'{date}\nfoo\n\n'
    client.post(course.get_unenroll_url(), form)
    assert Enrollment.active.count() == 0
    assert Enrollment.objects.first().reason_entry == f'{date}\nfoo\n\n'
    # Enroll for the second time, first entry reason should be saved
    form['reason'] = 'bar'
    client.post(course.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    assert Enrollment.objects.first().reason_entry == f'{date}\nbar\n\n{date}\nfoo\n\n'


@pytest.mark.django_db
def test_enrollment_leave_reason(client):
    student = StudentFactory()
    client.login(student)
    today = now_local(student.get_timezone())
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    co = CourseFactory(main_branch=student.branch, semester=current_semester)
    form = {'course_pk': co.pk}
    client.post(co.get_enroll_url(), form)
    assert Enrollment.active.count() == 1
    assert Enrollment.objects.first().reason_entry == ''
    form['reason'] = 'foo'
    client.post(co.get_unenroll_url(), form)
    assert Enrollment.active.count() == 0
    e = Enrollment.objects.first()
    assert today.strftime(DATE_FORMAT_RU) in e.reason_leave
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
def test_unenrollment(client, settings, assert_redirect):
    s = StudentFactory()
    client.login(s)
    current_semester = SemesterFactory.create_current()
    course = CourseFactory.create(main_branch=s.branch, semester=current_semester)
    as_ = AssignmentFactory.create_batch(3, course=course)
    form = {'course_pk': course.pk}
    # Enrollment already closed
    ep = EnrollmentPeriod.objects.get(semester=current_semester,
                                      site_id=settings.SITE_ID)
    today = timezone.now()
    ep.ends_on = (today - datetime.timedelta(days=1)).date()
    ep.save()
    response = client.post(course.get_enroll_url(), form)
    assert response.status_code == 403
    ep.ends_on = (today + datetime.timedelta(days=1)).date()
    ep.save()
    response = client.post(course.get_enroll_url(), form, follow=True)
    assert response.status_code == 200
    assert Enrollment.objects.count() == 1
    response = client.get(course.get_absolute_url())
    assert smart_bytes("Unenroll") in response.content
    assert smart_bytes(course) in response.content
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert not enrollment.is_deleted
    client.post(course.get_unenroll_url(), form)
    assert Enrollment.active.filter(student=s, course=course).count() == 0
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    enrollment_id = enrollment.pk
    assert enrollment.is_deleted
    # Make sure student progress won't been deleted
    a_ss = (StudentAssignment.objects.filter(student=s,
                                             assignment__course=course))
    assert len(a_ss) == 3
    # On re-enroll use old record
    client.post(course.get_enroll_url(), form)
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
    url = course.get_unenroll_url() + "?back=study:course_list"
    assert_redirect(client.post(url, form),
                    reverse('study:course_list'))
    assert set(a_ss) == set(StudentAssignment.objects
                                  .filter(student=s,
                                          assignment__course=course))
    # Check courses on student courses page are empty
    response = client.get(reverse("study:course_list"))
    assert len(response.context['ongoing_rest']) == 1
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['archive_enrolled']) == 0


@pytest.mark.django_db
def test_reenrollment(client):
    """Create assignments for student if they left the course and come back"""
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_other = BranchFactory()
    student = StudentFactory(branch=branch_spb)
    tomorrow = now_local(branch_spb.get_timezone()) + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(
        enrollment_period__ends_on=tomorrow.date())
    course = CourseFactory(main_branch=branch_spb, semester=term,
                           branches=[branch_other])
    assignment = AssignmentFactory(course=course)
    e = EnrollmentFactory(student=student, course=course)
    assert not e.is_deleted
    assert StudentAssignment.objects.filter(student_id=student.pk).count() == 1
    # Deactivate student enrollment
    e.is_deleted = True
    e.save()
    assert Enrollment.active.count() == 0
    assignment2 = AssignmentFactory(course=course)
    sg = StudentGroup.objects.get(course=course, branch=branch_other)
    # This assignment is restricted for student's group
    assignment3 = AssignmentFactory(course=course, restricted_to=[sg])
    assert StudentAssignment.objects.filter(student_id=student.pk).count() == 1
    client.login(student)
    form = {'course_pk': course.pk}
    response = client.post(course.get_enroll_url(), form, follow=True)
    assert response.status_code == 200
    e.refresh_from_db()
    assert StudentAssignment.objects.filter(student_id=student.pk).count() == 2


@pytest.mark.django_db
def test_enrollment_in_other_branch(client):
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(
        enrollment_period__ends_on=tomorrow.date())
    course_spb = CourseFactory(semester=term, main_branch__code=Branches.SPB)
    assert course_spb.enrollment_is_open
    student_spb = StudentFactory(branch__code=Branches.SPB)
    student_nsk = StudentFactory(branch__code=Branches.NSK)
    client.login(student_spb)
    form = {'course_pk': course_spb.pk}
    response = client.post(course_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(course_spb.get_enroll_url(), form)
    assert response.status_code == 403
    assert Enrollment.objects.count() == 1
    student = StudentFactory(branch__code='xxx')
    # Check button visibility
    Enrollment.objects.all().delete()
    client.login(student_spb)
    response = client.get(course_spb.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    buttons = (html.find("div", {"class": "o-buttons-vertical"})
               .find_all(attrs={'class': 'btn'}))
    assert any("Enroll in" in s.text for s in buttons)
    for user in [student_nsk, student]:
        client.login(user)
        response = client.get(course_spb.get_absolute_url())
        assert smart_bytes("Enroll in") not in response.content


@pytest.mark.django_db
def test_view_course_additional_branches(client):
    """
    Student could enroll in the course if it is available to the student branch
    """
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(
        enrollment_period__ends_on=tomorrow.date())
    course_spb = CourseFactory(main_branch__code=Branches.SPB,
                               semester=term)
    assert course_spb.enrollment_is_open
    student_spb = StudentFactory(branch=course_spb.main_branch)
    branch_nsk = BranchFactory(code=Branches.NSK)
    student_nsk = StudentFactory(branch=branch_nsk)
    form = {'course_pk': course_spb.pk}
    client.login(student_spb)
    response = client.post(course_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(course_spb.get_enroll_url(), form)
    assert response.status_code == 403
    CourseBranch(course=course_spb, branch=branch_nsk).save()
    response = client.post(course_spb.get_enroll_url(), form)
    assert response.status_code == 302
    assert Enrollment.objects.count() == 2


@pytest.mark.django_db
def test_course_enrollment_is_open(client, settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    co_spb = CourseFactory(semester=term, completed_at=tomorrow.date())
    assert co_spb.enrollment_is_open
    student_spb = StudentFactory(branch__code=Branches.SPB)
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
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") in response.content
    # What if enrollment not started yet
    ep = EnrollmentPeriod.objects.get(semester=term, site_id=settings.SITE_ID)
    ep.starts_on = tomorrow.date()
    ep.ends_on = tomorrow.date()
    ep.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content
    # Already completed
    ep.starts_on = yesterday.date()
    ep.ends_on = yesterday.date()
    ep.save()
    response = client.get(co_spb.get_absolute_url())
    assert smart_bytes("Enroll in") not in response.content


@pytest.mark.django_db
def test_enrollment_by_invitation(settings, client):
    future = now() + datetime.timedelta(days=3)
    term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    course_invitation = CourseInvitationFactory(course__semester=term)
    course = course_invitation.course
    enroll_url = course_invitation.get_absolute_url()
    invited = InvitedStudentFactory(branch=course.main_branch)
    client.login(invited)
    wrong_url = branch_aware_reverse(
        "course_enroll_by_invitation",
        kwargs={"course_token": "WRONG_TOKEN", **course.url_kwargs},
        subdomain=settings.LMS_SUBDOMAIN)
    response = client.post(wrong_url, {})
    assert response.status_code == 404
    response = client.post(enroll_url, {})
    assert response.status_code == 302
    enrollments = Enrollment.active.filter(student=invited, course=course).all()
    assert len(enrollments) == 1
