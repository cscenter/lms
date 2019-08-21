import factory
import pytest
from django.conf import settings

from courses.models import MetaCourse
from courses.tests.factories import MetaCourseFactory, SemesterFactory, \
    CourseFactory
from users.constants import Roles
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_meta_course_detail(client):
    mc = MetaCourseFactory.create()
    co1 = CourseFactory(meta_course=mc)
    co2 = CourseFactory(meta_course=mc)
    response = client.get(mc.get_absolute_url())
    assert response.status_code == 200
    assert mc.name.encode() in response.content
    assert mc.description.encode() in response.content


@pytest.mark.django_db
def test_meta_course_update_security(client, curator, assert_login_redirect):
    mc = MetaCourseFactory.create()
    url = mc.get_update_url()
    all_test_groups = [
        [],
        [Roles.TEACHER],
        [Roles.STUDENT],
        [Roles.GRADUATE]
    ]
    for groups in all_test_groups:
        client.login(UserFactory(groups=groups))
        assert_login_redirect(url, form={}, method='post')
        client.logout()
    client.login(curator)
    assert client.post(url, {'name': "foobar"}).status_code == 200


@pytest.mark.django_db
def test_meta_course_update(client, curator, assert_redirect):
    mc = MetaCourseFactory.create()
    client.login(curator)
    form = factory.build(dict, FACTORY_CLASS=MetaCourseFactory)
    form.update({
        'name_ru': "foobar",
        'description_ru': "foobar",
    })
    response = client.post(mc.get_update_url(), form)
    assert response.status_code == 302
    assert MetaCourse.objects.get(pk=mc.pk).name_ru == "foobar"
