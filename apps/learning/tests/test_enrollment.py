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
from core.urls import reverse
from courses.constants import AssignmentFormat
from courses.models import CourseBranch, CourseGroupModes, CourseTeacher
from courses.tests.factories import AssignmentFactory, CourseFactory, SemesterFactory
from learning.models import (
    Enrollment, EnrollmentPeriod, StudentAssignment, StudentGroup
)
from learning.services import EnrollmentService, StudentGroupService
from learning.services.enrollment_service import CourseCapacityFull
from learning.settings import Branches, StudentStatuses, EnrollmentTypes, InvitationEnrollmentTypes
from learning.tests.factories import (
    CourseInvitationFactory, EnrollmentFactory, StudentGroupFactory
)
from users.services import get_student_profile
from users.tests.factories import (
    InvitedStudentFactory, StudentFactory, StudentProfileFactory, TeacherFactory
)


@pytest.mark.django_db
def test_service_enroll(settings):
    student_profile, student_profile2 = StudentProfileFactory.create_batch(2)
    current_semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student_profile.branch,
                           semester=current_semester,
                           group_mode=CourseGroupModes.MANUAL)
    student_group = StudentGroupFactory(course=course)
    enrollment = EnrollmentService.enroll(student_profile, course, type=EnrollmentTypes.LECTIONS_ONLY,
                                          student_group=student_group, reason_entry='test enrollment')
    reason_entry = EnrollmentService._format_reason_record('test enrollment', course)
    assert enrollment.reason_entry == reason_entry
    assert enrollment.type == EnrollmentTypes.LECTIONS_ONLY
    assert not enrollment.is_deleted
    assert enrollment.student_group_id == student_group.pk
    student_group = StudentGroupService.resolve(course, student_profile=student_profile2)
    enrollment = EnrollmentService.enroll(student_profile2, course,
                                          reason_entry='test enrollment',
                                          student_group=student_group)
    assert enrollment.student_group == student_group
    assert enrollment.type == EnrollmentTypes.REGULAR


@pytest.mark.django_db
def test_enrollment_capacity(settings):
    student_profile = StudentProfileFactory()
    current_semester = SemesterFactory.create_current()
    course = CourseFactory.create(main_branch=student_profile.branch,
                                  semester=current_semester,
                                  capacity=1)
    student_group = course.student_groups.first()
    EnrollmentService.enroll(StudentProfileFactory(), course, student_group=student_group)
    course.refresh_from_db()
    assert course.places_left == 0
    assert Enrollment.active.count() == 1
    with pytest.raises(CourseCapacityFull):
        EnrollmentService.enroll(student_profile, course, student_group=student_group)
    # Make sure enrollment record created by enrollment service
    # was rollbacked by transaction context manager
    assert Enrollment.objects.count() == 1


@pytest.mark.django_db
def test_enrollment_capacity_view(client):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    client.login(student)
    future = now() + datetime.timedelta(days=2)
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date()
    )
    course = CourseFactory(main_branch=student_profile.branch,
                           semester=current_semester,)
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Places available")) not in response.content
    course.capacity = 1
    course.save()
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Places available")) in response.content
    client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert Enrollment.active.filter(student=student, course=course).count() == 1
    # Capacity is reached
    course.refresh_from_db()
    assert course.learners_count == 1
    assert course.places_left == 0
    s2 = StudentFactory(branch=course.main_branch)
    client.login(s2)
    response = client.get(course.get_absolute_url())
    assert smart_bytes(_("Enroll in")) not in response.content
    # POST request should be rejected
    response = client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    # Increase capacity
    course.capacity += 1
    course.save()
    assert course.places_left == 1
    response = client.get(course.get_absolute_url())
    assert (smart_bytes(_("Places available")) + b": 1") in response.content
    # Unenroll first student, capacity should increase
    client.login(student)
    client.post(course.get_unenroll_url())
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
    tomorrow = now_local(student.time_zone) + datetime.timedelta(days=1)
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
    today = now_local(student1.time_zone)
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    current_semester.save()
    course = CourseFactory(main_branch=student1.get_student_profile().branch,
                           semester=current_semester)
    url = course.get_enroll_url()
    response = client.post(url, data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    assert course.enrollment_set.count() == 1
    as_ = AssignmentFactory.create_batch(3, course=course)
    assert set((student1.pk, a.pk) for a in as_) == set(StudentAssignment.objects
                          .filter(student=student1)
                          .values_list('student', 'assignment'))
    co_other = CourseFactory(semester=current_semester)
    url = co_other.get_enroll_url()
    response = client.post(url, data={
        "type": EnrollmentTypes.REGULAR,
        "back": "study:course_list"
    })
    assert response.status_code == 302
    assert co_other.enrollment_set.count() == 1
    assert course.enrollment_set.count() == 1
    # Try to enroll to old CO
    old_semester = SemesterFactory.create(year=2010)
    old_co = CourseFactory.create(semester=old_semester)
    url = old_co.get_enroll_url()
    response = client.post(url, data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_enrollment_reason_entry(client):
    student_profile = StudentProfileFactory()
    client.login(student_profile.user)
    today = now_local(student_profile.user.time_zone)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    course = CourseFactory(main_branch=student_profile.branch, semester=current_term, ask_enrollment_reason=True)
    client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR,
        "reason": "foo"
    })
    assert Enrollment.active.count() == 1
    date = today.strftime(DATE_FORMAT_RU)
    assert Enrollment.objects.first().reason_entry == f'{date}\nfoo\n\n'
    client.post(course.get_unenroll_url())
    assert Enrollment.active.count() == 0
    assert Enrollment.objects.first().reason_entry == f'{date}\nfoo\n\n'
    # Enroll for the second time, first entry reason should be saved
    client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR,
        "reason": "bar"
    })
    assert Enrollment.active.count() == 1
    assert Enrollment.objects.first().reason_entry == f'{date}\nbar\n\n{date}\nfoo\n\n'


@pytest.mark.django_db
def test_enrollment_leave_reason(client):
    student_profile = StudentProfileFactory()
    client.login(student_profile.user)
    today = now_local(student_profile.user.time_zone)
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    co = CourseFactory(main_branch=student_profile.branch, semester=current_semester, ask_enrollment_reason=True)
    client.post(co.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert Enrollment.active.count() == 1
    assert Enrollment.objects.first().reason_entry == ''
    client.post(co.get_unenroll_url(), data={
        "type": EnrollmentTypes.REGULAR,
        "reason": "foo"
    })
    assert Enrollment.active.count() == 0
    e = Enrollment.objects.first()
    assert today.strftime(DATE_FORMAT_RU) in e.reason_leave
    assert 'foo' in e.reason_leave
    # Enroll for the second time and leave with another reason
    client.post(co.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert Enrollment.active.count() == 1
    client.post(co.get_unenroll_url(), data={
        "type": EnrollmentTypes.REGULAR,
        "reason": "bar"
    })
    assert Enrollment.active.count() == 0
    e = Enrollment.objects.first()
    assert 'foo' in e.reason_leave
    assert 'bar' in e.reason_leave
    co_other = CourseFactory.create(semester=current_semester)
    client.post(co_other.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    e_other = Enrollment.active.filter(course=co_other).first()
    assert not e_other.reason_entry
    assert not e_other.reason_leave


@pytest.mark.django_db
def test_unenrollment(client, settings, assert_redirect):
    student = StudentFactory()
    client.login(student)
    current_semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student.get_student_profile().branch, semester=current_semester)
    as_ = AssignmentFactory.create_batch(3, course=course)
    # Enrollment already closed
    ep = EnrollmentPeriod.objects.get(semester=current_semester,
                                      site_id=settings.SITE_ID)
    today = timezone.now()
    ep.ends_on = (today - datetime.timedelta(days=1)).date()
    ep.save()
    response = client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 403
    ep.ends_on = (today + datetime.timedelta(days=1)).date()
    ep.save()
    response = client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    response = client.get(course.get_absolute_url())
    assert smart_bytes("Unenroll") in response.content
    assert smart_bytes(course) in response.content
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert not enrollment.is_deleted
    client.post(course.get_unenroll_url())
    assert Enrollment.active.filter(student=student, course=course).count() == 0
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    enrollment_id = enrollment.pk
    assert enrollment.is_deleted
    # Make sure student progress won't been deleted
    a_ss = (StudentAssignment.objects.filter(student=student,
                                             assignment__course=course))
    assert len(a_ss) == 3
    # On re-enroll use old record
    client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert Enrollment.objects.count() == 1
    enrollment = Enrollment.objects.first()
    assert enrollment.pk == enrollment_id
    assert not enrollment.is_deleted
    # Check ongoing courses on student courses page are not empty
    response = client.get(reverse("study:course_list"))
    assert len(response.context_data['ongoing_rest']) == 0
    assert len(response.context_data['ongoing_enrolled']) == 1
    assert len(response.context_data['archive']) == 0
    # Check `back` url on unenroll action
    url = course.get_unenroll_url() + "?back=study:course_list"
    response = client.post(url, data={
        "type": EnrollmentTypes.REGULAR
    })
    assert_redirect(response, reverse('study:course_list'))
    assert set(a_ss) == set(StudentAssignment.objects
                                  .filter(student=student,
                                          assignment__course=course))
    # Check courses on student courses page are empty
    response = client.get(reverse("study:course_list"))
    assert len(response.context_data['ongoing_rest']) == 1
    assert len(response.context_data['ongoing_enrolled']) == 0
    assert len(response.context_data['archive']) == 0


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
    response = client.post(course.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
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
    student_profile_spb = StudentProfileFactory(branch__code=Branches.SPB)
    student_profile_nsk = StudentProfileFactory(branch__code=Branches.NSK)
    client.login(student_profile_spb.user)
    response = client.post(course_spb.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_profile_nsk.user)
    response = client.post(course_spb.get_enroll_url(),  data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 403
    assert Enrollment.objects.count() == 1
    student_profile = StudentProfileFactory(branch__code='xxx')
    # Check button visibility
    Enrollment.objects.all().delete()
    client.login(student_profile_spb.user)
    response = client.get(course_spb.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    buttons = (html.find("div", {"class": "o-buttons-vertical"})
               .find_all(attrs={'class': 'btn'}))
    assert any("Enroll in" in s.text for s in buttons)
    for user in [student_profile_nsk.user, student_profile.user]:
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
    client.login(student_spb)
    response = client.post(course_spb.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    assert Enrollment.objects.count() == 1
    client.login(student_nsk)
    response = client.post(course_spb.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 403
    CourseBranch(course=course_spb, branch=branch_nsk).save()
    response = client.post(course_spb.get_enroll_url(), data={
        "type": EnrollmentTypes.REGULAR
    })
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
    wrong_url = reverse(
        "course_enroll_by_invitation",
        kwargs={"course_token": "WRONG_TOKEN", **course.url_kwargs},
        subdomain=settings.LMS_SUBDOMAIN)
    response = client.post(wrong_url)
    assert response.status_code == 404
    response = client.get(enroll_url)
    html = response.content.decode()
    assert response.status_code == 200
    assert "Как вы хотите записаться на курс?" in html
    response = client.post(enroll_url, data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    enrollments = Enrollment.active.filter(student=invited, course=course).all()
    assert len(enrollments) == 1
    unenroll_url = course.get_unenroll_url()
    client.post(unenroll_url)
    assert not Enrollment.active.filter(student=invited, course=course).exists()
    course_invitation.enrollment_type = InvitationEnrollmentTypes.LECTIONS_ONLY
    course_invitation.save()
    response = client.get(enroll_url)
    assert response.status_code == 302
    enrollments = Enrollment.active.filter(student=invited, course=course).all()
    assert len(enrollments) == 1
    assert enrollments.first().type == EnrollmentTypes.LECTIONS_ONLY


@pytest.mark.django_db
def test_enrollment_populate_assignments(client):
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_spb = BranchFactory(code=Branches.SPB)
    student_profile = StudentProfileFactory(branch=branch_spb)
    student = student_profile.user
    today = now_local(student.time_zone)
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today.date())
    course = CourseFactory(main_branch=branch_spb,
                           branches=[branch_nsk],
                           semester=current_semester)
    assert StudentGroup.objects.count() == 2
    student_group_spb = StudentGroup.objects.get(branch=branch_spb)
    student_group_nsk = StudentGroup.objects.get(branch=branch_nsk)
    assignment_all = AssignmentFactory(course=course)
    assignment_spb = AssignmentFactory(course=course, restricted_to=[student_group_spb])
    assignment_nsk = AssignmentFactory(course=course, restricted_to=[student_group_nsk])
    assert StudentAssignment.objects.count() == 0
    client.login(student)
    enroll_url = course.get_enroll_url()
    response = client.post(enroll_url, data={
        "type": EnrollmentTypes.REGULAR
    })
    assert response.status_code == 302
    assert course.enrollment_set.count() == 1
    student_assignments = StudentAssignment.objects.filter(student=student)
    assert student_assignments.count() == 2
    assignments = [sa.assignment for sa in student_assignments]
    assert assignment_all in assignments
    assert assignment_spb in assignments


@pytest.mark.django_db
def test_enrollment_add_student_to_project(mocker, django_capture_on_commit_callbacks):
    course = CourseFactory()
    mocked = mocker.patch("code_reviews.gerrit.tasks.add_student_to_gerrit_project.delay")
    AssignmentFactory(course=course,
                      submission_type=AssignmentFormat.ONLINE)
    EnrollmentFactory(course=course)
    # Not called because there is no code review assignments
    mocked.assert_not_called()
    mocked.reset_mock()

    AssignmentFactory(course=course,
                      submission_type=AssignmentFormat.CODE_REVIEW)
    with django_capture_on_commit_callbacks(execute=True):
        EnrollmentFactory(course=course)
    mocked.assert_called_once()


@pytest.mark.django_db
def test_enrollment_add_teacher_to_project(mocker, django_capture_on_commit_callbacks):
    course = CourseFactory()
    mocked = mocker.patch("code_reviews.gerrit.tasks.add_teacher_to_gerrit_project.delay")
    # need to register receiver function
    from code_reviews.gerrit.signals import post_save_teacher
    AssignmentFactory(course=course,
                      submission_type=AssignmentFormat.ONLINE)
    t1, t2 = TeacherFactory.create_batch(2)
    CourseTeacher(course=course, teacher=t1).save()
    # Not called because there is no code review assignments
    mocked.assert_not_called()
    mocked.reset_mock()

    AssignmentFactory(course=course,
                      submission_type=AssignmentFormat.CODE_REVIEW)
    CourseTeacher(course=course, teacher=t2).save()
    mocked.assert_called_once()



