import csv
import io
import re
from bs4 import BeautifulSoup
import pytest
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.constants import SemesterTypes
from courses.tests.factories import CourseFactory, SemesterFactory
from learning.settings import GradeTypes, StudentStatuses
from learning.tests.factories import EnrollmentFactory
from users.models import StudentTypes
from users.tests.factories import CuratorFactory, PartnerTagFactory, StudentFactory, StudentProfileFactory

@pytest.mark.django_db
def test_enrolees_selection_views_security(client):
    student = StudentFactory()
    curator = CuratorFactory()
    semester = SemesterFactory.create_current()
    SemesterFactory.create_prev(semester)
    course = CourseFactory(semester=semester)
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
    SemesterFactory.create_prev(current_semester)
    course = CourseFactory(semester=current_semester)
    url = reverse("staff:enrolees_selection_list")
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    if current_semester.type == SemesterTypes.AUTUMN:
        other_semester = SemesterFactory.create_next(current_semester)  
    else:
        other_semester = SemesterFactory.create_prev(current_semester)
    assert html.find(text=str(current_semester).capitalize()) is not None
    assert html.find(text=str(other_semester).capitalize()) is not None
    assert html.find(text=course.main_branch.name) is not None
    # enrolees_selection_list.html does not has jinja templates, so there is no ability to get rid of external spaces after the course name
    # Have to use re to find substring as html.find returns the string that exactly match given string
    assert html.find(text=re.compile(str(course.meta_course))) is not None
    other_course = CourseFactory(semester=other_semester)
    response = client.get(url)
    html = BeautifulSoup(response.content, "html.parser")
    assert html.find(text=str(current_semester).capitalize()) is not None
    assert html.find(text=str(other_semester).capitalize()) is not None
    assert html.find(text=course.main_branch.name) is not None
    assert html.find(text=other_course.main_branch.name) is not None
    assert html.find(text=re.compile(str(course.meta_course))) is not None
    assert html.find(text=re.compile(str(other_course.meta_course))) is not None
    
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
        "Partner",
        "Curriculum year",
        "Enrollment type",
        "Entry reason",
        "Average grade"
    ]
    answers_csv = client.get(csv_download_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(answers_csv)) if s]
    assert data == [headers]


    enrollment_one = EnrollmentFactory(course=course, student=student_one)
    enrollment_two = EnrollmentFactory(course=course, student=student_two)
    student_profile_one = enrollment_one.student_profile
    student_profile_one.year_of_curriculum = student_profile_one.year_of_admission
    student_profile_one.student_type = StudentTypes.PARTNER
    student_profile_one.partner = PartnerTagFactory()
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
        student_profile_one.partner.name,
        str(student_profile_one.year_of_curriculum),
        enrollment_one.get_type_display(),
        "",
        ""
    ]

    student_two_row = [
        student_two.get_absolute_url(),
        student_two.last_name,
        student_two.first_name,
        student_two.patronymic,
        student_profile_two.branch.name,
        student_profile_two.get_type_display(),
        "",
        str(student_profile_two.year_of_curriculum),
        enrollment_two.get_type_display(),
        "",
        ""
    ]

    status_log_csv = client.get(csv_download_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(status_log_csv)) if s]
    assert len(data) == 3
    assert data[1] == student_one_row
    assert data[2] == student_two_row
    
    enrollment_one.reason_entry = "reason one"
    enrollment_one.save()
    enrollment_two.reason_entry = "reason two"
    enrollment_two.save()
    student_one.patronymic = ""
    student_one.save()
    branch = BranchFactory()
    student_profile_two.branch = branch
    student_profile_two.save()

    student_one_row[-2] = "reason one"
    student_one_row[3] = ""
    student_two_row[-2] = "reason two"
    student_two_row[4] = branch.name

    status_log_csv = client.get(csv_download_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(status_log_csv)) if s]
    assert len(data) == 3
    assert data[1] == student_one_row
    assert data[2] == student_two_row
    
@pytest.mark.django_db
def test_enrolees_selection_csv_view_calculate_average_grades(client):
    curator = CuratorFactory()
    client.login(curator)
    student = StudentFactory()
    invited_profile = StudentProfileFactory(user=student, 
                                            type=StudentTypes.INVITED)
    
    course = CourseFactory()
    csv_download_url = course.get_enrolees_selection_url()
    def assert_average_grade_is(value):
        status_log_csv = client.get(csv_download_url).content.decode('utf-8')
        data = [s for s in csv.reader(io.StringIO(status_log_csv)) if s]
        assert len(data) == 2
        assert data[1][-1] == (str(round(value, 3)) if value is not None else "")
    
    EnrollmentFactory(course=course, 
                        student=student,
                        student_profile=invited_profile,
                        grade=GradeTypes.GOOD)
    assert_average_grade_is(None)
    
    normal_profile = StudentProfileFactory(user=student, 
                                           status=StudentStatuses.ACADEMIC_LEAVE,
                                           year_of_admission=student.date_joined.year - 1)
    [EnrollmentFactory(student=student, student_profile=normal_profile, grade=grade) for grade in [GradeTypes.GOOD, GradeTypes.EXCELLENT]]
    EnrollmentFactory(student=student,
                        student_profile=normal_profile,
                        grade=GradeTypes.CREDIT,
                        course__is_visible_in_certificates=False)
    assert_average_grade_is((4+5)/2)
    
    partner_profile = StudentProfileFactory(user=student, 
                                            type=StudentTypes.PARTNER)
    [EnrollmentFactory(student=student, student_profile=partner_profile, grade=grade) for grade in [GradeTypes.CREDIT, GradeTypes.CREDIT, GradeTypes.RE_CREDIT]]
    
    assert_average_grade_is((4+5+3+3)/4)
    
    expelled_profile = StudentProfileFactory(user=student)
    expelled_profile.status = StudentStatuses.EXPELLED
    expelled_profile.save()
    [EnrollmentFactory(student=student, student_profile=expelled_profile, grade=grade) for grade in [GradeTypes.CREDIT, GradeTypes.CREDIT]]
    
    assert_average_grade_is((4+5+3+3)/4)