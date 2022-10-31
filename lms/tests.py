import datetime
from pprint import pprint

import factory
import pytest
from django.conf import settings

from django.contrib.sites.models import Site
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from core.tests.factories import BranchFactory, SiteFactory
from core.urls import reverse
from core.utils import instance_memoize
from courses.constants import SemesterTypes
from courses.models import CourseTeacher
from courses.tests.factories import CourseFactory, CourseTeacherFactory, SemesterFactory
from learning.invitation.views import complete_student_profile
from learning.settings import Branches, GradeTypes, StudentStatuses
from learning.tests.factories import EnrollmentFactory, CourseInvitationFactory
from users.constants import Roles
from users.models import StudentTypes, User, StudentProfile
from users.services import create_student_profile, update_student_status
from users.tests.factories import TeacherFactory, UserFactory, StudentFactory, CuratorFactory, StudentProfileFactory


@pytest.mark.django_db
def test_login_restrictions(client, settings):
    current_site = SiteFactory(pk=settings.SITE_ID)
    branch = BranchFactory(site=current_site)
    user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
    user_data["branch"] = branch
    student = User.objects.create_user(**user_data)
    # Try to login without groups at all
    response = client.post(reverse('auth:login'), user_data)
    assert response.status_code == 200
    assert len(response.context["form"].errors) > 0
    # Login as student
    create_student_profile(user=student, branch=branch, profile_type=StudentTypes.REGULAR,
                           year_of_admission=now().year,
                           year_of_curriculum=now().year)
    instance_memoize.delete_cache(student)
    student.refresh_from_db()
    response = client.post(reverse('auth:login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Student role from another site can't log in
    new_site = Site(domain='foo.bar.baz', name='foo_bar_baz')
    new_site.save()
    student.groups.all().delete()
    create_student_profile(user=student, branch=BranchFactory(site=new_site),
                           profile_type=StudentTypes.REGULAR,
                           year_of_admission=now().year,
                           year_of_curriculum=now().year)
    response = client.post(reverse('auth:login'), user_data, follow=True)
    assert not response.wsgi_request.user.is_authenticated
    # And teacher
    client.logout()
    student.groups.all().delete()
    student.add_group(Roles.TEACHER, site_id=new_site.id)
    response = client.post(reverse('auth:login'), user_data, follow=True)
    assert not response.wsgi_request.user.is_authenticated
    # Login as volunteer
    student.groups.all().delete()
    create_student_profile(user=student, branch=branch, profile_type=StudentTypes.VOLUNTEER,
                           year_of_admission=now().year,
                           year_of_curriculum=now().year)
    response = client.post(reverse('auth:login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as volunteer while having student role from another site
    create_student_profile(user=student, branch=BranchFactory(site=new_site),
                           profile_type=StudentTypes.REGULAR,
                           year_of_admission=now().year,
                           year_of_curriculum=now().year)
    response = client.post(reverse('auth:login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as graduate only
    student.groups.all().delete()
    student.add_group(Roles.GRADUATE)
    response = client.post(reverse('auth:login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()


@pytest.mark.django_db
def test_view_course_offering_teachers_visibility(client, settings):
    """Spectator should not be displayed as course teacher"""
    teacher, spectator = TeacherFactory.create_batch(2)
    co_1 = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=co_1, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    co_2 = CourseFactory()
    CourseTeacherFactory(course=co_2, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    url = reverse('course_list', subdomain=settings.LMS_SUBDOMAIN)
    client.login(teacher)
    response = client.get(url)
    assert smart_bytes(teacher.get_full_name()) in response.content
    assert smart_bytes(spectator.get_full_name()) not in response.content


@pytest.mark.django_db
def test_view_course_offerings_permission(client, settings, assert_login_redirect):
    url = reverse('course_list', subdomain=settings.LMS_SUBDOMAIN)
    assert_login_redirect(url)
    student = StudentFactory()
    client.login(student)
    assert client.get(url).status_code == 200
    client.login(TeacherFactory())
    assert client.get(url).status_code == 200
    client.login(CuratorFactory())
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_view_course_offerings(client):
    """Course offerings should show all courses except summer term courses"""
    url = reverse('course_list', subdomain=settings.LMS_SUBDOMAIN)
    autumn_term = SemesterFactory(year=2022,
                                  type=SemesterTypes.AUTUMN)
    summer_term = SemesterFactory(year=autumn_term.year - 1,
                                  type=SemesterTypes.SUMMER)
    spring_term = SemesterFactory(year=autumn_term.year - 1,
                                  type=SemesterTypes.SPRING)
    student = UserFactory()
    regular_profile = StudentProfileFactory(user=student)
    client.login(student)

    autumn_courses = CourseFactory.create_batch(3, semester=autumn_term)
    spring_courses = CourseFactory.create_batch(2, semester=spring_term)
    CourseFactory.create_batch(7, semester=summer_term)

    enrolled_curr, unenrolled_curr, can_enroll_curr = autumn_courses
    enrolled_prev = spring_courses[0]
    EnrollmentFactory(student=student,
                      student_profile=regular_profile,
                      course=enrolled_curr)
    EnrollmentFactory(student=student,
                      student_profile=regular_profile,
                      course=unenrolled_curr,
                      is_deleted=True)
    EnrollmentFactory(student=student,
                      student_profile=regular_profile,
                      course=enrolled_prev)
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    assert len(terms_courses) == 2  # two terms
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == len(autumn_courses) + len(spring_courses)


@pytest.mark.django_db
def test_view_course_offerings_invited_restriction(client):
    """Invited students should only see courses
    for which they were enrolled or invited"""
    url = reverse('course_list', subdomain=settings.LMS_SUBDOMAIN)
    future = now() + datetime.timedelta(days=3)
    autumn_term = SemesterFactory.create_current(enrollment_period__ends_on=future.date())
    site = SiteFactory(id=settings.SITE_ID)
    course_invitation = CourseInvitationFactory(course__semester=autumn_term)
    student_profile = StudentProfileFactory(type=StudentTypes.INVITED)
    student = student_profile.user
    complete_student_profile(student, site, course_invitation.invitation)

    autumn_courses = CourseFactory.create_batch(3, semester=autumn_term)
    enrolled_curr, unenrolled_curr, can_enroll_curr = autumn_courses
    EnrollmentFactory(student=student,
                      student_profile=student_profile,
                      course=enrolled_curr)
    EnrollmentFactory(student=student,
                      student_profile=student_profile,
                      course=unenrolled_curr,
                      is_deleted=True)

    client.login(student)
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == 1
    assert terms_courses[0][0]['name'] == enrolled_curr.meta_course.name

    response = client.get(course_invitation.invitation.get_absolute_url())
    assert response.status_code == 200
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == 2


@pytest.mark.django_db
def test_view_course_offerings_old_invited(client):
    """Invited student sees only old courses on which has been enrolled."""
    url = reverse('course_list', subdomain=settings.LMS_SUBDOMAIN)
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(enrollment_period__ends_on=future.date())
    previous_term = SemesterFactory(year=current_term.year - 1, type=SemesterTypes.SPRING)

    site = SiteFactory(id=settings.SITE_ID)
    course_invitation = CourseInvitationFactory(course__semester=previous_term)
    student = UserFactory()
    complete_student_profile(student, site, course_invitation.invitation)
    student_profile = StudentProfile.objects.get(user=student)
    random_course = CourseFactory(semester=current_term)
    old_course = CourseFactory(semester=previous_term)
    enrollment = EnrollmentFactory(course=old_course,
                                   student=student,
                                   student_profile=student_profile,
                                   grade=GradeTypes.UNSATISFACTORY)

    client.login(student)
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == 1

    enrollment.is_deleted = True
    enrollment.save()
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == 0

    course_invitation.invitation.enrolled_students.add(student_profile)
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == 1

    new_invited_profile = StudentProfileFactory(type=StudentTypes.INVITED,
                                                user=student,
                                                year_of_admission=current_term.year)
    complete_student_profile(student, site, course_invitation.invitation)
    assert student.get_student_profile() == new_invited_profile

    course_invitation.invitation.enrolled_students.add(student_profile)
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    # Unenrolled access to previous semester courses has been revoked
    assert founded_courses == 0

    enrollment.is_deleted = False
    enrollment.save()
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    # But the courses the student was enrolled in are still available
    assert founded_courses == 1


@pytest.mark.django_db
def test_view_course_offerings_regular_in_academic(client):
    url = reverse('course_list', subdomain=settings.LMS_SUBDOMAIN)
    future = now() + datetime.timedelta(days=3)
    current_term = SemesterFactory.create_current(enrollment_period__ends_on=future.date())

    regular_profile = StudentProfileFactory()
    student = regular_profile.user

    course_enrolled, random_course = CourseFactory.create_batch(2)
    enrollment = EnrollmentFactory(course=course_enrolled,
                                   student=student,
                                   student_profile=regular_profile,
                                   grade=GradeTypes.UNSATISFACTORY)

    curator = CuratorFactory()
    update_student_status(student_profile=regular_profile,
                          new_status=StudentStatuses.EXPELLED,
                          editor=curator)

    client.login(student)
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    # Expelled student still have access to courses
    assert founded_courses == 2

    site = SiteFactory(id=settings.SITE_ID)
    course_invitation = CourseInvitationFactory(course__semester=current_term)
    new_invited_profile = StudentProfileFactory(type=StudentTypes.INVITED,
                                                user=student,
                                                year_of_admission=current_term.year)
    complete_student_profile(student, site, course_invitation.invitation)

    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    # Show only the course the student was enrolled in
    assert founded_courses == 1

    client.get(course_invitation.invitation.get_absolute_url())
    response = client.get(url)
    terms_courses = list(response.context_data['courses'].values())
    founded_courses = sum(map(len, terms_courses))
    assert founded_courses == 2
