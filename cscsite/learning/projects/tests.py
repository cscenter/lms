# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_bytes

from learning.factories import SemesterFactory
from learning.projects.factories import ProjectFactory
from learning.settings import GRADES, STUDENT_STATUS


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
