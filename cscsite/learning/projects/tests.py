# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_bytes

from learning.factories import SemesterFactory
from learning.projects.factories import ProjectFactory


@pytest.mark.django_db
def test_user_detail(client, student_center_factory):
    """
    Students should have `projects` in their info on profile page.

    Just a simple test to check something appears.
    """
    student = student_center_factory(enrollment_year='2013')
    semester1 = SemesterFactory.create(year=2014, type='spring')
    semester2 = SemesterFactory.create(year=2014, type='autumn')
    sp1 = ProjectFactory.create(students=[student], semester=semester1)
    sp2 = ProjectFactory.create(students=[student],
                                semester=semester2,
                                description="")
    resp = client.get(reverse('user_detail', args=[student.pk]))
    assert smart_bytes(sp1.name) in resp.content
    assert smart_bytes(sp1.description) in resp.content
    assert smart_bytes(sp2.name) in resp.content
