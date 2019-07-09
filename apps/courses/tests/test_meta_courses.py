import factory
import pytest
from django.conf import settings
from django.forms import model_to_dict

from courses.tests.factories import MetaCourseFactory, SemesterFactory, CourseFactory
from courses.models import MetaCourse
from users.constants import Roles
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_meta_course_detail(client):
    mc = MetaCourseFactory.create()
    s1 = SemesterFactory(year=2016)
    s2 = SemesterFactory(year=2017)
    co1 = CourseFactory(semester=s1, meta_course=mc,
                        city=settings.DEFAULT_CITY_CODE)
    co2 = CourseFactory(semester=s2, meta_course=mc,
                        city=settings.DEFAULT_CITY_CODE)
    response = client.get(mc.get_absolute_url())
    assert response.status_code == 200
    assert mc.name.encode() in response.content
    assert mc.description.encode() in response.content
    assert {c.pk for c in response.context['courses']} == {co1.pk, co2.pk}
    co2.city_id = "kzn"
    co2.save()
    response = client.get(mc.get_absolute_url())
    if settings.SITE_ID == settings.CENTER_SITE_ID:
        assert {c.pk for c in response.context['courses']} == {co1.pk}


@pytest.mark.django_db
def test_meta_course_update_security(client, assert_login_redirect):
    mc = MetaCourseFactory.create()
    url = mc.get_update_url()
    all_test_groups = [
        [],
        [Roles.TEACHER],
        [Roles.STUDENT],
        [Roles.GRADUATE]
    ]
    for groups in all_test_groups:
        client.login(UserFactory.create(groups=groups, city_id='spb'))
        assert_login_redirect(url, form={}, method='post')
        client.logout()
    client.login(UserFactory.create(is_superuser=True, is_staff=True))
    assert client.post(url, {'name': "foobar"}).status_code == 200


@pytest.mark.django_db
def test_meta_course_update(client, assert_redirect):
    mc = MetaCourseFactory.create()
    client.login(UserFactory.create(is_superuser=True, is_staff=True))
    form = factory.build(dict, FACTORY_CLASS=MetaCourseFactory)
    form.update({
        'name_ru': "foobar",
        'description_ru': "foobar",
    })
    response = client.post(mc.get_update_url(), form)
    assert response.status_code == 302
    assert MetaCourse.objects.get(pk=mc.pk).name_ru == "foobar"
