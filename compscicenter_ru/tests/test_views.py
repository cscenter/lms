import datetime

import pytest

from django.contrib.sites.models import Site
from django.core.cache import cache

from core.models import Branch
from core.tests.factories import BranchFactory
from core.tests.settings import ANOTHER_DOMAIN_ID
from core.urls import reverse
from courses.services import CourseService
from learning.models import GraduateProfile
from learning.settings import Branches
from learning.tests.factories import (
    CourseFactory, GraduateProfileFactory, MetaCourseFactory
)
from study_programs.tests.factories import AcademicDisciplineFactory


# TODO: test context
@pytest.mark.django_db
def test_testimonials_smoke(client):
    GraduateProfileFactory(testimonial='test', photo='stub.JPG')
    response = client.get(reverse('testimonials'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_stayhome_smoke(client):
    response = client.get(reverse('stay_home'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_enrollment_checklist(client):
    """Make sure template is rendered without errors"""
    response = client.get(reverse("enrollment_checklist"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_alumni(client, settings):
    url_alumni_all = reverse('alumni')
    response = client.get(url_alumni_all)
    assert response.status_code == 404  # No graduates yet
    graduated_on = datetime.date(year=2015, month=1, day=1)
    graduated = GraduateProfileFactory(graduated_on=graduated_on)
    cache_key_pattern = GraduateProfile.HISTORY_CACHE_KEY_PATTERN
    site = Site.objects.get(pk=settings.SITE_ID)
    cache_key = cache_key_pattern.format(site_id=site.pk)
    cache.delete(cache_key)
    response = client.get(url_alumni_all)
    assert response.status_code == 200
    json_data = response.context_data['app_data']
    assert not json_data['props']['areaOptions']
    assert len(json_data['props']['yearOptions']) == 1
    assert json_data['props']['yearOptions'] == [{'label': '2015', 'value': 2015}]
    assert json_data['state']['year'] == json_data['props']['yearOptions'][0]
    a = AcademicDisciplineFactory(code='ds')
    response = client.get(url_alumni_all)
    json_data = response.context_data['app_data']
    assert json_data['props']['areaOptions'] == [{'label': a.name, 'value': a.pk}]


@pytest.mark.django_db
def test_meta_course_detail(client, settings):
    mc = MetaCourseFactory()
    meta_course_url = reverse('meta_course_detail',
                              kwargs={'course_slug': mc.slug})
    response = client.get(meta_course_url)
    assert response.status_code == 200
    assert not response.context_data['grouped_courses']
    course1, course2 = CourseFactory.create_batch(2, meta_course=mc)
    response = client.get(meta_course_url)
    assert response.status_code == 200
    assert mc.name.encode() in response.content
    assert mc.description.encode() in response.content
    grouped_courses = response.context_data['grouped_courses']
    assert len(grouped_courses) == 1
    branch_spb = BranchFactory(code=Branches.SPB)
    key = (branch_spb.code, branch_spb.name)
    assert key in grouped_courses
    assert {c.pk for c in grouped_courses[key]} == {course1.pk, course2.pk}
    assert 'tabs' in response.context_data
    assert len(response.context_data['tabs']) == 1
    # Relocate course to the non-target branch
    branch = BranchFactory(site_id=ANOTHER_DOMAIN_ID)
    course2.main_branch = branch
    course2.save()
    CourseService.sync_branches(course2)
    response = client.get(meta_course_url)
    grouped_courses = response.context_data['grouped_courses']
    assert {c.pk for c in grouped_courses[key]} == {course1.pk}
    # Return to another cs center branch
    course2.main_branch = Branch.objects.get(code=Branches.NSK,
                                             site_id=settings.SITE_ID)
    course2.save()
    CourseService.sync_branches(course2)
    response = client.get(meta_course_url)
    assert len(response.context_data['tabs']) == 2
    assert len(response.context_data['grouped_courses']) == 2

