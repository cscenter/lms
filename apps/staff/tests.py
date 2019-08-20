import pytest
from django.utils.encoding import smart_bytes

from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.settings import StudentStatuses, GradeTypes
from projects.tests.factories import ProjectFactory
from users.tests.factories import StudentFactory


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client):
    student = StudentFactory(enrollment_year='2013',
                             status=StudentStatuses.WILL_GRADUATE)
    semester1 = SemesterFactory.create(year=2014, type='spring')
    p = ProjectFactory.create(students=[student], semester=semester1)
    sp = p.projectstudent_set.all()[0]
    sp.final_grade = GradeTypes.GOOD
    sp.save()
    client.login(curator)
    response = client.get(reverse('staff:exports_students_diplomas_tex',
                                  kwargs={"branch_id": student.branch_id}))
    assert smart_bytes(p.name) in response.content
