from datetime import date

import pytest
from django.utils.encoding import smart_bytes

from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.settings import StudentStatuses, GradeTypes
from learning.tests.factories import GraduateProfileFactory
from projects.tests.factories import ProjectFactory
from users.tests.factories import StudentFactory, CuratorFactory


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client, settings):
    student = StudentFactory(student_profile__status=StudentStatuses.WILL_GRADUATE)
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


@pytest.mark.django_db
def test_official_diplomas_list_view(client):
    # 2-digit day and month to avoid bothering with zero padding
    date1 = date(2020, 12, 20)
    date2 = date(2020, 11, 15)
    g1, g2 = GraduateProfileFactory.create_batch(2, diploma_issued_on=date1)
    g3 = GraduateProfileFactory(diploma_issued_on=date2)

    curator = CuratorFactory()
    client.login(curator)
    response = client.get(reverse('staff:exports_official_diplomas_list', kwargs={
        'year': date1.year, 'month': date1.month, 'day': date1.day
    }))
    assert smart_bytes(g1.student_profile.user.get_full_name(last_name_first=True)) in response.content
    assert smart_bytes(g2.student_profile.user.get_full_name(last_name_first=True)) in response.content
    assert smart_bytes(g3.student_profile.user.get_full_name(last_name_first=True)) not in response.content
