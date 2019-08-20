import datetime

import pytest
from django.core.cache import cache

from core.models import Branch
from core.tests.factories import CityFactory, BranchFactory
from core.urls import reverse
from learning.settings import Branches
from learning.tests.factories import GraduateProfileFactory, MetaCourseFactory, CourseFactory
from study_programs.tests.factories import AcademicDisciplineFactory


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
    response = client.get(mc.get_absolute_url())
    assert response.status_code == 200
    assert not response.context_data['grouped_courses']
    course1, course2 = CourseFactory.create_batch(2, meta_course=mc)
    response = client.get(mc.get_absolute_url())
    assert response.status_code == 200
    assert mc.name.encode() in response.content
    assert mc.description.encode() in response.content
    grouped_courses = response.context_data['grouped_courses']
    assert len(grouped_courses) == 1
    assert Branches.SPB in grouped_courses
    assert {c.pk for c in grouped_courses[Branches.SPB]} == {course1.pk,
                                                             course2.pk}
    assert 'tabs' in response.context_data
    assert len(response.context_data['tabs']) == 1
    # Relocate 1 course to the city out of the cs center branches
    city = CityFactory(code='xxx')
    branch = BranchFactory(city=city)
    course2.branch = branch
    course2.save()
    response = client.get(mc.get_absolute_url())
    grouped_courses = response.context_data['grouped_courses']
    assert {c.pk for c in grouped_courses[Branches.SPB]} == {course1.pk}
    # Return to another cs center branch
    course2.branch = Branch.objects.get(code=Branches.NSK,
                                        site_id=settings.SITE_ID)
    course2.save()
    response = client.get(mc.get_absolute_url())
    assert len(response.context_data['tabs']) == 2
    assert len(response.context_data['grouped_courses']) == 2

