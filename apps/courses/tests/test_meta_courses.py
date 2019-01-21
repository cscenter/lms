import pytest
from django.conf import settings
from django.forms import model_to_dict
from django.urls import reverse

from courses.tests.factories import MetaCourseFactory, SemesterFactory, CourseFactory
from courses.models import MetaCourse
from users.constants import AcademicRoles
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
def test_meta_course_update_security(client, assert_redirect):
    mc = MetaCourseFactory.create()
    url = reverse('meta_course_edit', args=[mc.slug])
    all_test_groups = [
        [],
        [AcademicRoles.TEACHER_CENTER],
        [AcademicRoles.STUDENT_CENTER],
        [AcademicRoles.GRADUATE_CENTER]
    ]
    for groups in all_test_groups:
        client.login(UserFactory.create(groups=groups, city_id='spb'))
        assert_redirect(client.post(url, {}),
                        "{}?next={}".format(settings.LOGIN_URL, url))
        client.logout()
    client.login(UserFactory.create(is_superuser=True, is_staff=True))
    assert client.post(url, {'name': "foobar"}).status_code == 200


@pytest.mark.django_db
def test_meta_course_update(client, assert_redirect):
    mc = MetaCourseFactory.create()
    client.login(UserFactory.create(is_superuser=True, is_staff=True))
    form = model_to_dict(mc)
    form.update({'name_ru': "foobar"})
    response = client.post(mc.get_update_url(), form)
    assert response.status_code == 302
    assert MetaCourse.objects.get(pk=mc.pk).name_ru == "foobar"
