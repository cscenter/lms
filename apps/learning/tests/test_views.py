import datetime
import logging

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.timezone import now
from testfixtures import LogCapture

from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from auth.permissions import perm_registry
from core.tests.factories import SiteFactory, BranchFactory
from core.timezone import now_local
from core.urls import reverse
from courses.models import CourseTeacher
from courses.tests.factories import *
from learning.invitation.views import complete_student_profile, is_student_profile_valid
from learning.permissions import ViewEnrollment
from learning.settings import GradeTypes, StudentStatuses, EnrollmentTypes
from learning.tests.factories import *
from users.models import StudentTypes, StudentProfile
from users.services import update_student_status
from users.tests.factories import (
    CuratorFactory, StudentFactory, TeacherFactory, UserFactory, StudentProfileFactory
)


@pytest.mark.django_db
def test_course_list_view_permissions(client, assert_login_redirect):
    url = reverse('teaching:course_list')
    assert_login_redirect(url)
    student = StudentFactory()
    client.login(student)
    assert client.get(url).status_code == 403
    client.login(TeacherFactory())
    assert client.get(url).status_code == 200
    client.login(CuratorFactory())
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_course_list_view_add_news_btn_visibility(client):
    """Add news button should be hidden for users without
    CreateCourseNews permission"""
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)

    def has_add_news_btn(user):
        url = reverse('teaching:course_list')
        client.login(user)
        html = client.get(url).content.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        return soup.find('a', {
            "href": course.get_create_news_url()
        }) is not None

    assert has_add_news_btn(teacher)
    assert not has_add_news_btn(spectator)


@pytest.mark.django_db
def test_course_detail_view_basic_get(client, assert_login_redirect):
    course = CourseFactory()
    assert_login_redirect(course.get_absolute_url())
    client.login(StudentFactory())
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    url = reverse('courses:course_detail', kwargs={
        "course_id": course.pk,
        "course_slug": "space-odyssey",
        "main_branch_id": course.main_branch_id,
        "semester_year": 2010,
        "semester_type": "autumn",
    })
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_course_detail_view_invited_permission(client):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())

    invitation_1 = CourseInvitationFactory(course__semester=current_term)
    invitation_2 = CourseInvitationFactory(course__semester=current_term)
    invitation = invitation_1.invitation
    branch = BranchFactory()
    student = UserFactory(branch=branch)
    assert not is_student_profile_valid(student, branch.site)
    complete_student_profile(student, branch.site, invitation)

    client.login(student)
    response = client.get(invitation_1.course.get_absolute_url())
    assert response.status_code == 200
    response = client.get(invitation.get_absolute_url())
    assert response.status_code == 200
    assert 'Записаться' in response.content.decode('utf-8')
    response = client.get(invitation_1.course.get_absolute_url())
    assert response.status_code == 200
    response = client.get(invitation_2.course.get_absolute_url())
    assert response.status_code == 403

    invitation_1.invitation.delete()
    response = client.get(invitation_1.course.get_absolute_url())
    assert response.status_code == 403

@pytest.mark.django_db
def test_invitation_view_is_active(client):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())

    course_invitation_1 = CourseInvitationFactory(course__semester=current_term)
    invitation = course_invitation_1.invitation
    course_invitation_2 = CourseInvitationFactory(course__semester=current_term, invitation=invitation)
    branch = BranchFactory()
    student = UserFactory(branch=branch)
    complete_student_profile(student, branch.site, invitation)

    client.login(student)
    response = client.get(invitation.get_absolute_url())
    assert response.status_code == 200
    assert 'class="btn btn-primary">Записаться</a>' in response.content.decode('utf-8')
    assert '<div class="btn btn-primary disabled">Записаться</div>' not in response.content.decode('utf-8')
    course_invitation_2.course.completed_at = now().date()
    course_invitation_2.course.save()
    
    response = client.get(invitation.get_absolute_url())
    assert response.status_code == 200
    assert 'class="btn btn-primary">Записаться</a>' in response.content.decode('utf-8')
    assert '<div class="btn btn-primary disabled">Записаться</div>' in response.content.decode('utf-8')
    course_invitation_1.course.completed_at = now().date()
    course_invitation_1.course.save()
    
    response = client.get(invitation.get_absolute_url())
    assert response.status_code == 404


@pytest.mark.django_db
def test_course_detail_view_enrolled_invited_capabilities(client):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    course_invitation = CourseInvitationFactory(course__semester=current_term)
    course = course_invitation.course
    invitation = course_invitation.invitation

    site = SiteFactory(id=settings.SITE_ID)
    branch = BranchFactory(site=site)
    student = UserFactory(branch=branch)
    client.login(student)
    response = client.get(course.get_absolute_url())
    assert response.status_code == 403

    assert not is_student_profile_valid(student, site)
    complete_student_profile(student, site, invitation)
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    url = course_invitation.get_absolute_url()
    response = client.get(course_invitation.invitation.get_absolute_url())
    assert response.status_code == 200
    assert 'Записаться' in response.content.decode('utf-8')
    client.post(url, data={
        "type": EnrollmentTypes.REGULAR
    })

    enrollment = Enrollment.objects.get(invitation=course_invitation.invitation)
    enrollment.invitation = None
    enrollment.save()
    course_invitation.invitation.delete()
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200

    enrollment.grade = GradeTypes.UNSATISFACTORY
    enrollment.save()
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200

    enrollment.delete()
    response = client.get(course.get_absolute_url())
    assert response.status_code == 403


@pytest.mark.django_db
def test_course_detail_view_inactive_regular_active_invited_profile_permission(client):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    previous_term = SemesterFactory.create_prev(term=current_term)
    course_invitation = CourseInvitationFactory(course__semester=current_term)
    course = course_invitation.course
    invitation = course_invitation.invitation

    site = SiteFactory(id=settings.SITE_ID)
    branch = BranchFactory(site=site)
    student = StudentFactory(student_profile__year_of_admission=previous_term.year - 1, branch=branch)
    regular_profile = student.get_student_profile(site=site)

    client.login(student)
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200

    enrollment = EnrollmentFactory(student=student,
                                   student_profile=regular_profile)
    response = client.get(enrollment.course.get_absolute_url())
    assert response.status_code == 200

    curator = CuratorFactory()
    update_student_status(student_profile=regular_profile,
                          new_status=StudentStatuses.ACADEMIC_LEAVE,
                          editor=curator)

    assert not is_student_profile_valid(student, site)
    complete_student_profile(student, site, invitation)
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    response = client.get(enrollment.course.get_absolute_url())
    assert response.status_code == 200
    enrollment.grade = GradeTypes.UNSATISFACTORY
    enrollment.save()
    response = client.get(enrollment.course.get_absolute_url())
    assert response.status_code == 200
    enrollment.is_deleted = True
    enrollment.save()
    response = client.get(enrollment.course.get_absolute_url())
    assert response.status_code == 403


@pytest.mark.django_db
def test_course_detail_view_inactive_invited_profile_permission(client):
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    previous_term = SemesterFactory.create_prev(term=current_term)
    site = SiteFactory(id=settings.SITE_ID)
    course_invitation = CourseInvitationFactory(course__semester=previous_term)
    branch = BranchFactory(site=site)
    student = UserFactory(branch=branch)
    assert not is_student_profile_valid(student, site)
    complete_student_profile(student, site, course_invitation.invitation)
    student_profile = StudentProfile.objects.get(user=student)
    old_course = CourseFactory(semester=previous_term)
    enrollment = EnrollmentFactory(course=old_course, student=student, student_profile=student_profile)

    client.login(student)
    response = client.get(course_invitation.course.get_absolute_url())
    assert response.status_code == 403

    response = client.get(old_course.get_absolute_url())
    assert response.status_code == 200

    enrollment.grade = GradeTypes.UNSATISFACTORY
    response = client.get(old_course.get_absolute_url())
    assert response.status_code == 200

    course_invitation = CourseInvitationFactory(course__semester=current_term)
    complete_student_profile(student, site, course_invitation.invitation)
    new_student_profile = StudentProfile.objects.get(user=student)
    assert student.get_student_profile() == new_student_profile

    response = client.get(old_course.get_absolute_url())
    assert response.status_code == 200

    # Because not has been enrolled through old profile
    response = client.get(course_invitation.course.get_absolute_url())
    assert response.status_code == 403


@pytest.mark.django_db
def test_course_detail_view_course_user_relations(client):
    """
    Testing is_enrolled and is_actual_teacher here
    """
    student = StudentFactory()
    teacher = TeacherFactory()
    co = CourseFactory.create()
    co_other = CourseFactory.create()
    url = co.get_absolute_url()
    client.login(student)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    EnrollmentFactory(student=student, course=co_other)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    EnrollmentFactory(student=student, course=co)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is not None
    assert not ctx['is_actual_teacher']
    client.logout()
    client.login(teacher)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    CourseTeacherFactory(course=co_other, teacher=teacher)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert not ctx['is_actual_teacher']
    CourseTeacherFactory(course=co, teacher=teacher)
    ctx = client.get(url).context_data
    assert ctx['request_user_enrollment'] is None
    assert ctx['is_actual_teacher']


@pytest.mark.django_db
def test_course_detail_view_assignment_list(client, assert_login_redirect):
    student = StudentFactory()
    teacher = TeacherFactory()
    today = now_local(student.time_zone).date()
    next_day = today + datetime.timedelta(days=1)
    course = CourseFactory(teachers=[teacher],
                           semester=SemesterFactory.create_current(),
                           completed_at=next_day)
    course_url = course.get_absolute_url()
    EnrollmentFactory(student=student, course=course)
    a = AssignmentFactory.create(course=course)
    assert_login_redirect(course_url)
    client.login(student)
    assert smart_bytes(a.title) in client.get(course_url).content
    a_s = StudentAssignment.objects.get(assignment=a, student=student)
    assert smart_bytes(a_s.get_student_url()) in client.get(course_url).content
    a_s.delete()
    with LogCapture(level=logging.INFO) as l:
        assert client.get(course_url).status_code == 200
        l.check(('learning.tabs',
                 'INFO',
                 f"no StudentAssignment for "
                 f"student ID {student.pk}, assignment ID {a.pk}"))
    client.login(teacher)
    assert smart_bytes(a.title) in client.get(course_url).content
    assert smart_bytes(a.get_teacher_url()) in client.get(course_url).content


@pytest.mark.django_db
def test_view_course_edit_description_security(client, assert_login_redirect):
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory.create(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    url = course.get_update_url()
    assert_login_redirect(url)

    client.login(teacher_other)
    response = client.get(url)
    assert response.status_code == 403
    client.logout()

    client.login(spectator)
    response = client.get(url)
    assert response.status_code == 403
    client.logout()

    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_events_smoke(client):
    evt = EventFactory.create()
    url = evt.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 200
    assert evt.name.encode() in response.content
    assert smart_bytes(evt.venue.get_absolute_url()) in response.content


@pytest.mark.django_db
def test_view_course_student_progress_security(client, lms_resolver):
    student = StudentFactory()
    enrollment = EnrollmentFactory(student=student)
    url = reverse('teaching:student-progress', kwargs={
        "enrollment_id": enrollment.pk,
        **enrollment.course.url_kwargs
    })
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewEnrollment.name
    assert resolver.func.view_class.permission_required in perm_registry
    user = UserFactory()
    response = client.get(url)
    assert response.status_code == 302
    client.login(user)
    response = client.get(url)
    assert response.status_code == 403
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
