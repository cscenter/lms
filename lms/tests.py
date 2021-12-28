from pprint import pprint

import factory
import pytest

from django.contrib.sites.models import Site
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from core.tests.factories import BranchFactory, SiteFactory
from core.urls import reverse
from core.utils import instance_memoize
from courses.models import CourseTeacher
from courses.tests.factories import CourseFactory, CourseTeacherFactory
from users.constants import Roles
from users.models import StudentTypes, User
from users.services import create_student_profile
from users.tests.factories import TeacherFactory, UserFactory


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

