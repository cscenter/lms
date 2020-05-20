import pytest
from django.utils.encoding import smart_bytes

from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.settings import StudentStatuses, GradeTypes
from projects.tests.factories import ProjectFactory
from users.tests.factories import StudentFactory, CuratorFactory, \
    StudentProfileFactory


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client):
    student = StudentFactory(status=StudentStatuses.WILL_GRADUATE)
    semester1 = SemesterFactory.create(year=2014, type='spring')
    p = ProjectFactory.create(students=[student], semester=semester1)
    sp = p.projectstudent_set.all()[0]
    sp.final_grade = GradeTypes.GOOD
    sp.save()
    client.login(curator)
    response = client.get(reverse('staff:exports_students_diplomas_tex',
                                  kwargs={"branch_id": student.branch_id}))
    assert smart_bytes(p.name) in response.content


@pytest.mark.django_db
def test_view_student_progress_report_full_download_csv(client):
    url = reverse("staff:students_progress_report",
                  kwargs={'output_format': 'csv'})
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'


@pytest.mark.django_db
def test_view_student_progress_report_for_term(client):
    curator = CuratorFactory()
    client.login(curator)
    term = SemesterFactory.create_current()
    url = reverse("staff:students_progress_report_for_term", kwargs={
        'output_format': 'csv', 'term_type': term.type, 'term_year': term.year
    })
    response = client.get(url)
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv; charset=utf-8'


@pytest.mark.django_db
def test_view_student_faces_smoke(client):
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(reverse('staff:student_faces'))
    assert response.status_code == 200
