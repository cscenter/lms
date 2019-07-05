import factory
import pytest
from django.contrib.sites.models import Site

from core.urls import reverse
from users.constants import AcademicRoles
from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_login_restrictions(client, settings):
    """
    Make sure users with any roles for compscicenter.ru could log in.
    """
    settings.SITE_ID = settings.CENTER_SITE_ID
    new_site = Site(domain='foo.bar.baz', name='foo_bar_baz')
    new_site.save()
    user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
    student = User.objects.create_user(**user_data)
    # Try to login without groups at all
    response = client.post(reverse('login'), user_data)
    assert response.status_code == 200
    assert len(response.context["form"].errors) > 0
    # Login as student
    student.add_group(AcademicRoles.STUDENT)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Student role from another site can't log in
    student.groups.all().delete()
    student.add_group(AcademicRoles.STUDENT, site_id=new_site.id)
    response = client.post(reverse('login'), user_data, follow=True)
    assert not response.wsgi_request.user.is_authenticated
    # And teacher
    client.logout()
    student.groups.all().delete()
    student.add_group(AcademicRoles.TEACHER, site_id=new_site.id)
    response = client.post(reverse('login'), user_data, follow=True)
    assert not response.wsgi_request.user.is_authenticated
    # Login as volunteer
    student.groups.all().delete()
    student.add_group(AcademicRoles.VOLUNTEER)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as volunteer and student role from another site
    student.add_group(AcademicRoles.STUDENT, site_id=new_site.id)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
    # Login as graduate only
    student.groups.all().delete()
    student.add_group(AcademicRoles.GRADUATE)
    response = client.post(reverse('login'), user_data, follow=True)
    assert response.wsgi_request.user.is_authenticated
    client.logout()
