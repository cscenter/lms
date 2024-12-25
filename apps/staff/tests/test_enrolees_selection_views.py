import csv
import io
import re
from bs4 import BeautifulSoup
import pytest
from django.conf import settings
from django.contrib.messages import get_messages

from core.models import Branch
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.tests.factories import CourseFactory, SemesterFactory
from learning.settings import StudentStatuses
from learning.tests.factories import EnrollmentFactory
from staff.tests.factories import StudentStatusLogFactory, StudentAcademicDisciplineLogFactory
from study_programs.tests.factories import AcademicDisciplineFactory
from users.tests.factories import CuratorFactory, StudentFactory, UserFactory

@pytest.mark.django_db
def test_enrolees_selection_views_security(client):
    student = StudentFactory()
    curator = CuratorFactory()
    course = CourseFactory(semester=SemesterFactory.create_current())
    urls = (reverse("staff:enrolees_selection_list"), course.get_enrolees_selection_url())
    client.login(student)
    for url in urls:
        response = client.get(url)
        assert response.status_code == 302
        assert response.url.startswith("/login/?next=/staff/enrolees-selection/")
    client.login(curator)
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200

@pytest.mark.django_db
def test_enrolees_selection_list_view(client):
    curator = CuratorFactory()
    current_semester = SemesterFactory.create_current()
    course = CourseFactory(semester=current_semester)
    url = reverse("staff:enrolees_selection_list")
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    next_semester = SemesterFactory.create_next(current_semester)
    assert html.find(text=str(current_semester).capitalize()) is not None
    assert html.find(text=str(next_semester).capitalize()) is not None
    assert html.find(text=course.main_branch.name) is not None
    # enrolees_selection_list.html does not has jinja templates, so there is no ability to get rid of external spaces after the course name
    # Have to use re to find substring as html.find returns the string that exactly match given string
    assert html.find(text=re.compile(str(course.meta_course))) is not None
    next_course = CourseFactory(semester=next_semester)
    response = client.get(url)
    html = BeautifulSoup(response.content, "html.parser")
    assert html.find(text=str(current_semester).capitalize()) is not None
    assert html.find(text=str(next_semester).capitalize()) is not None
    assert html.find(text=course.main_branch.name) is not None
    assert html.find(text=next_course.main_branch.name) is not None
    assert html.find(text=re.compile(str(course.meta_course))) is not None
    assert html.find(text=re.compile(str(next_course.meta_course))) is not None
    
@pytest.mark.django_db
def test_enrolees_selection_csv_view(client):
    curator = CuratorFactory()
    student_one, student_two = StudentFactory.create_batch(2)
    course = CourseFactory()
    csv_download_url = course.get_enrolees_selection_url()
    client.login(curator)

    headers = [
        "User url",
        "Last name",
        "First name",
        "Patronymic",
        "Branch",
        "Student type",
        "Curriculum year",
        "Enrollment type",
        "Entry reason"
    ]
    answers_csv = client.get(csv_download_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(answers_csv)) if s]
    assert data == [headers]


    enrollment_one = EnrollmentFactory(course=course, student=student_one)
    enrollment_two = EnrollmentFactory(course=course, student=student_two)
    student_profile_one = enrollment_one.student_profile
    student_profile_one.year_of_curriculum = student_profile_one.year_of_admission
    student_profile_one.save()
    student_profile_two = enrollment_two.student_profile
    student_profile_two.year_of_curriculum = student_profile_two.year_of_admission
    student_profile_two.save()

    student_one_row = [
        student_one.get_absolute_url(),
        student_one.last_name,
        student_one.first_name,
        student_one.patronymic,
        student_profile_one.branch.name,
        student_profile_one.get_type_display(),
        str(student_profile_one.year_of_curriculum),
        enrollment_one.get_type_display(),
        ""
    ]

    student_two_row = [
        student_two.get_absolute_url(),
        student_two.last_name,
        student_two.first_name,
        student_two.patronymic,
        student_profile_two.branch.name,
        student_profile_two.get_type_display(),
        str(student_profile_two.year_of_curriculum),
        enrollment_two.get_type_display(),
        ""
    ]

    status_log_csv = client.get(csv_download_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(status_log_csv)) if s]
    assert len(data) == 3
    assert data[1] == student_two_row
    assert data[2] == student_one_row
    
    enrollment_one.reason_entry = "reason one"
    enrollment_one.save()
    enrollment_two.reason_entry = "reason two"
    enrollment_two.save()
    student_one.patronymic = ""
    student_one.save()
    branch = BranchFactory()
    student_profile_two.branch = branch
    student_profile_two.save()

    student_one_row[-1] = "reason one"
    student_one_row[3] = ""
    student_two_row[-1] = "reason two"
    student_two_row[4] = branch.name

    status_log_csv = client.get(csv_download_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(status_log_csv)) if s]
    assert len(data) == 3
    assert data[1] == student_two_row
    assert data[2] == student_one_row