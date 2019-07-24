import datetime

import pytest
from django.core.cache import cache

from core.urls import reverse
from learning.tests.factories import AcademicDisciplineFactory, \
    GraduateProfileFactory, MetaCourseFactory, CourseFactory


# TODO: test context
@pytest.mark.django_db
def test_testimonials_smoke(client):
    GraduateProfileFactory(testimonial='test', photo='stub.JPG')
    response = client.get(reverse('testimonials'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_alumni(client):
    url_alumni_all = reverse('alumni')
    response = client.get(url_alumni_all)
    assert response.status_code == 200
    json_data = response.context_data['app_data']
    assert json_data['props']['years'] == [{'label': 2013, 'value': 2013}]
    assert not json_data['props']['areas']
    graduated_on = datetime.date(year=2015, month=1, day=1)
    graduated = GraduateProfileFactory(graduated_on=graduated_on)
    cache.delete('cscenter_last_graduation_year')
    response = client.get(url_alumni_all)
    assert response.status_code == 200
    json_data = response.context_data['app_data']
    assert len(json_data['props']['years']) == 3
    assert json_data['props']['years'][0]['value'] == 2015
    assert json_data['state']['year'] == json_data['props']['years'][0]
    a = AcademicDisciplineFactory()
    response = client.get(url_alumni_all)
    json_data = response.context_data['app_data']
    assert json_data['props']['areas'] == [{'label': a.name, 'value': a.code}]


@pytest.mark.django_db
def test_meta_course_detail(client, settings):
    mc = MetaCourseFactory()
    co1, co2 = CourseFactory.create_batch(2, meta_course=mc, city=settings.DEFAULT_CITY_CODE)
    response = client.get(mc.get_absolute_url())
    assert response.status_code == 200
    assert mc.name.encode() in response.content
    assert mc.description.encode() in response.content
    grouped_courses = response.context_data['grouped_courses']
    assert len(grouped_courses) == 1
    assert settings.DEFAULT_CITY_CODE in grouped_courses
    assert {c.pk for c in grouped_courses[settings.DEFAULT_CITY_CODE]} == {co1.pk, co2.pk}
    co2.city_id = "kzn"
    co2.save()
    response = client.get(mc.get_absolute_url())
    grouped_courses = response.context_data['grouped_courses']
    assert {c.pk for c in grouped_courses[settings.DEFAULT_CITY_CODE]} == {co1.pk}

