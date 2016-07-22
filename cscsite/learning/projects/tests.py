# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_bytes

from learning.factories import SemesterFactory
from learning.projects.factories import ProjectFactory
from learning.settings import GRADES, STUDENT_STATUS, PARTICIPANT_GROUPS
from learning.utils import get_current_semester_pair

URL_REVIEWER_PROJECTS = reverse("projects:reviewer_projects")


@pytest.mark.django_db
def test_user_detail(client, student_center_factory):
    """
    Students should have `projects` in their info on profile page.

    Just a simple test to check something appears.
    """
    student = student_center_factory(enrollment_year='2013')
    semester1 = SemesterFactory.create(year=2014, type='spring')
    semester2 = SemesterFactory.create(year=2014, type='autumn')
    p1 = ProjectFactory.create(students=[student], semester=semester1)
    p2 = ProjectFactory.create(students=[student],
                               semester=semester2,
                               description="")
    sp2 = p2.projectstudent_set.all()[0]
    sp2.final_grade = GRADES.good
    sp2.save()
    resp = client.get(reverse('user_detail', args=[student.pk]))
    assert smart_bytes(p1.name) in resp.content
    assert smart_bytes(p1.description) in resp.content
    assert smart_bytes(p2.name) in resp.content
    assert smart_bytes(sp2.get_final_grade_display().lower()) in resp.content


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client, student_center_factory):
    student = student_center_factory(enrollment_year='2013',
                                     status=STUDENT_STATUS.will_graduate)
    semester1 = SemesterFactory.create(year=2014, type='spring')
    p = ProjectFactory.create(students=[student], semester=semester1)
    sp = p.projectstudent_set.all()[0]
    sp.final_grade = GRADES.good
    sp.save()
    client.login(curator)
    response = client.get(reverse('staff_exports_students_diplomas'))
    assert smart_bytes(p.name) in response.content


@pytest.mark.django_db
def test_reviewer_list_security(client,
                                student_center_factory,
                                user_factory,
                                curator):
    """Check ProjectReviewerOnlyMixin"""
    url = "{}?show=active".format(URL_REVIEWER_PROJECTS)
    response = client.get(url)
    assert response.status_code == 302
    student = student_center_factory()
    client.login(student)
    response = client.get(url)
    assert response.status_code == 302
    reviewer = user_factory.create(groups=[PARTICIPANT_GROUPS.PROJECT_REVIEWER])
    client.login(reviewer)
    response = client.get(url)
    assert response.status_code == 200
    assert not response.context["projects"]
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_reviewer_list(client, user_factory, curator, student_center_factory):
    url_active = "{}?show=active".format(URL_REVIEWER_PROJECTS)
    url_available = "{}?show=available".format(URL_REVIEWER_PROJECTS)
    url_archive = "{}?show=archive".format(URL_REVIEWER_PROJECTS)
    url_all = "{}?show=all".format(URL_REVIEWER_PROJECTS)
    reviewer = user_factory.create(groups=[PARTICIPANT_GROUPS.PROJECT_REVIEWER])
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    client.login(reviewer)
    student = student_center_factory()
    response = client.get(url_active)
    assert response.status_code == 200
    assert len(response.context["projects"]) == 0
    # Enroll on project from prev term
    project = ProjectFactory(students=[student], reviewers=[reviewer],
                             semester=semester_prev)
    response = client.get(url_active)
    assert response.status_code == 200
    assert len(response.context["projects"]) == 0
    # Enroll on project from current term
    project = ProjectFactory(students=[student], reviewers=[reviewer],
                             semester=semester)
    response = client.get(url_active)
    assert len(response.context["projects"]) == 1
    # On page with all projects show projects from current term to reviewers
    response = client.get(url_available)
    assert len(response.context["projects"]) == 1
    client.login(curator)
    response = client.get(url_active)
    assert len(response.context["projects"]) == 0
    response = client.get(url_available)
    assert len(response.context["projects"]) == 1
    response = client.get(url_all)
    assert len(response.context["projects"]) == 2


