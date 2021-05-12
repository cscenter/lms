import datetime

import pytest

from core.tests.factories import BranchFactory
from core.tests.settings import ANOTHER_DOMAIN_ID
from core.urls import reverse_lazy
from courses.constants import SemesterTypes
from courses.tests.factories import CourseFactory, MetaCourseFactory, SemesterFactory
from learning.settings import Branches, GradeTypes, StudentStatuses
from learning.tests.factories import EnrollmentFactory, GraduateFactory
from study_programs.tests.factories import AcademicDisciplineFactory
from users.models import StudentTypes
from users.tests.factories import (
    CuratorFactory, StudentFactory, UserFactory, VolunteerFactory
)


@pytest.fixture(scope="module")
def search_url():
    return reverse_lazy('staff:student_search_json')


@pytest.mark.django_db
def test_student_search_by_name(client, search_url, settings):
    curator = CuratorFactory()
    client.login(curator)
    student = StudentFactory(student_profile__year_of_admission=2011,
                             student_profile__year_of_curriculum=2011,
                             student_profile__status="",
                             last_name="Иванов",
                             first_name="Иван")
    response = client.get(f"{search_url}?name=лол")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    # 1 symbol is too short to apply filter by name
    # but students will be searched anyway since lookup isn't empty
    response = client.get(f"{search_url}?name=и")
    assert response.status_code == 200
    assert response.json()["count"] == 1
    response = client.get(f"{search_url}?name=ан")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    # Make sure `ts_vector` works fine with single quotes
    response = client.get(f"{search_url}?name=%27d")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_student_search(client, curator, search_url, settings):
    """Simple test cases to make sure, multi values still works"""
    student = StudentFactory(student_profile__year_of_admission=2011,
                             student_profile__year_of_curriculum=2011,
                             student_profile__status="",
                             last_name='Иванов',
                             first_name='Иван')
    StudentFactory(student_profile__year_of_admission=2011,
                   student_profile__year_of_curriculum=2011,
                   student_profile__status="",
                   last_name='Иванов',
                   first_name='Иван')
    StudentFactory(student_profile__year_of_admission=2012,
                   student_profile__year_of_curriculum=2012,
                   student_profile__status=StudentStatuses.EXPELLED,
                   last_name='Иванов',
                   first_name='Иван')
    branch = BranchFactory(site_id=ANOTHER_DOMAIN_ID)
    StudentFactory(last_name='Сидоров', first_name='Сидор',
                   student_profile__year_of_admission=2011,
                   student_profile__year_of_curriculum=2011,
                   student_profile__branch=branch)
    volunteer = VolunteerFactory(student_profile__year_of_admission=2011,
                                 student_profile__status="")

    response = client.get(search_url)
    assert response.status_code == 401
    client.login(curator)
    # Empty results by default
    response = client.get(search_url)
    assert response.status_code == 200
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(search_url, "year_of_curriculum=2011"))
    # Club users, volunteers are not included since curriculum year is empty
    assert response.json()["count"] == 2
    # 2011 | 2012 years
    response = client.get("{}?{}".format(search_url,
                                         "year_of_curriculum=2011%2C2012"))
    assert response.json()["count"] == 3
    # Now test groups filter
    response = client.get("{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types={}".format(StudentTypes.REGULAR)
    ))
    assert response.json()["count"] == 2
    response = client.get("{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types={}".format(StudentTypes.VOLUNTEER)
    ))
    assert response.json()["count"] == 0, "curriculum year for volunteer is not set"
    response = client.get("{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types[]={}&types[]={}".format(
            StudentTypes.REGULAR, StudentTypes.VOLUNTEER
        )
    ))
    assert response.json()["count"] == 2
    student_profile = student.get_student_profile(settings.SITE_ID)
    student_profile.status = StudentStatuses.REINSTATED
    student_profile.save()
    response = client.get("{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types[]={}&status={}".format(
            StudentTypes.REGULAR,
            StudentStatuses.REINSTATED
        )
    ))
    assert response.json()["count"] == 1
    response = client.get("{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types={},{}&status={}&cnt_enrollments={}".format(
            StudentTypes.REGULAR,
            StudentTypes.VOLUNTEER,
            StudentStatuses.REINSTATED,
            "2"
        )
    ))
    assert response.json()["count"] == 0
    # Check multi values still works for cnt_enrollments
    response = client.get("{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types={}&status={}&cnt_enrollments={}".format(
            StudentTypes.REGULAR,
            StudentStatuses.REINSTATED,
            "0,2"
        )
    ))
    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_student_search_enrollments(client, curator, search_url):
    """
    Count successfully passed courses instead of course_offerings.
    """
    client.login(curator)
    student = StudentFactory(student_profile__year_of_curriculum=2011,
                             student_profile__status="",
                             last_name='Иванов', first_name='Иван')
    ENROLLMENTS_URL = "{}?{}".format(
        search_url,
        "year_of_curriculum=2011&types={},{}&cnt_enrollments={{}}".format(
            StudentTypes.REGULAR,
            StudentTypes.VOLUNTEER,
        )
    )
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 0
    response = client.get(ENROLLMENTS_URL.format("0,2"))
    assert response.json()["count"] == 1
    s1 = SemesterFactory.create(year=2014, type=SemesterTypes.SPRING)
    s2 = SemesterFactory.create(year=2014, type=SemesterTypes.AUTUMN)
    mc1, mc2 = MetaCourseFactory.create_batch(2)
    co1 = CourseFactory.create(meta_course=mc1, semester=s1)
    co2 = CourseFactory.create(meta_course=mc1, semester=s2)
    e1 = EnrollmentFactory.create(student=student, course=co1,
                                  grade=GradeTypes.GOOD)
    e2 = EnrollmentFactory.create(student=student, course=co2,
                                  grade=GradeTypes.NOT_GRADED)
    response = client.get(ENROLLMENTS_URL.format("1"))
    assert response.json()["count"] == 1
    e2.grade = GradeTypes.GOOD
    e2.save()
    response = client.get(ENROLLMENTS_URL.format("1"))
    assert response.json()["count"] == 1
    co3 = CourseFactory.create(meta_course=mc2)
    EnrollmentFactory.create(student=student, grade=GradeTypes.GOOD, course=co3)
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 1
    other_student = StudentFactory(student_profile__year_of_curriculum=2011)
    e3 = EnrollmentFactory.create(student=other_student, grade=GradeTypes.GOOD)
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 1
    response = client.get(ENROLLMENTS_URL.format("1,2"))
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_student_search_by_types(client, curator, search_url, settings):
    client.login(curator)
    # All users below are considered as `studying` due to empty status
    branch = BranchFactory(site_id=ANOTHER_DOMAIN_ID)
    StudentFactory.create_batch(2, student_profile__branch=branch)
    students = StudentFactory.create_batch(
        3,
        student_profile__year_of_admission=2011,
        student_profile__year_of_curriculum=2011,
        student_profile__status="")
    volunteers = VolunteerFactory.create_batch(
        4,
        student_profile__year_of_admission=2011,
        student_profile__year_of_curriculum=2011,
        student_profile__status="")
    # Empty results if no query provided
    response = client.get(search_url)
    assert response.json()["count"] == 0
    # And without any value it still empty
    response = client.get("{}?{}".format(search_url, "types="))
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(search_url, "status=studying&types="))
    json_data = response.json()
    assert json_data["count"] == len(students) + len(volunteers)
    graduated = GraduateFactory(student_profile__year_of_admission=2012,
                                student_profile__year_of_curriculum=2012,
                                student_profile__status="",
                                student_profile__site_id=ANOTHER_DOMAIN_ID)
    url = f"{search_url}?status=studying&types={StudentTypes.REGULAR}&year_of_curriculum=2011,2012"
    response = client.get(url)
    assert response.json()["count"] == len(students)


@pytest.mark.django_db
def test_student_search_by_branch(client, curator, search_url):
    client.login(curator)
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    _ = UserFactory.create(branch=branch_spb)  # random user
    students_spb = StudentFactory.create_batch(3,
                                               student_profile__year_of_admission=2011,
                                               student_profile__status="", branch=branch_spb)
    students_nsk = StudentFactory.create_batch(2,
                                               student_profile__year_of_admission=2011,
                                               student_profile__status="", branch=branch_nsk)
    # Send empty query
    response = client.get("{}?{}".format(search_url, "branches="))
    assert response.json()["count"] == 0
    response = client.get("{}?branches={}".format(search_url, branch_spb.pk))
    json_data = response.json()
    assert json_data["count"] == len(students_spb)
    assert {s.pk for s in students_spb} == {r["user_id"] for r in
                                            json_data["results"]}
    response = client.get(
        f"{search_url}?branches={branch_spb.pk},{branch_nsk.pk}")
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)
    # All with status `studying`
    response = client.get(f"{search_url}?status=studying&branches=")
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)


@pytest.mark.django_db
def test_student_by_virtual_status_studying(client, curator, search_url):
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    client.login(curator)
    students_spb = StudentFactory.create_batch(
        4, student_profile__year_of_admission=2011, student_profile__status="",
        branch=branch_spb)
    students_nsk = StudentFactory.create_batch(
        7, student_profile__year_of_admission=2011, student_profile__status="",
        branch=branch_nsk)
    volunteers = VolunteerFactory.create_batch(
        3, student_profile__year_of_admission=2011, student_profile__status="",
        branch=branch_spb)
    graduated_on = datetime.date(year=2017, month=1, day=1)
    graduated = GraduateFactory.create_batch(
        5, branch=branch_spb, student_profile__status='',
        student_profile__year_of_admission=2011,
        graduate_profile__graduated_on=graduated_on)
    response = client.get("{}?{}".format(search_url, "status=studying"))
    json_data = response.json()
    total_studying = len(students_spb) + len(students_nsk) + len(volunteers)
    assert json_data["count"] == total_studying
    # Add some students with inactive status
    expelled = StudentFactory.create_batch(
        2, student_profile__year_of_admission=2011,
        student_profile__status=StudentStatuses.EXPELLED,
        branch=branch_spb)
    response = client.get("{}?{}".format(search_url, "status=studying"))
    json_data = response.json()
    assert json_data["count"] == total_studying
    # Test `studying` includes `will_graduate` and `reinstated` statuses
    response = client.get("{}?{}".format(search_url,
                                         "status=studying,will_graduate"))
    assert response.json()["count"] == total_studying
    url = "{}?{}".format(search_url, "status=studying,will_graduate,reinstated")
    response = client.get(url)
    assert response.json()["count"] == total_studying
    # More precisely by group
    url = "{}?{}".format(
        search_url, "status=studying&types={}".format(StudentTypes.VOLUNTEER))
    response = client.get(url)
    assert response.json()["count"] == len(volunteers)
    query = f"status=studying,{StudentStatuses.GRADUATE}&types={StudentTypes.VOLUNTEER}"
    response = client.get("{}?{}".format(search_url, query))
    assert response.json()["count"] == len(volunteers)


@pytest.mark.django_db
def test_student_search_academic_disciplines(settings, client, search_url):
    branch_spb = BranchFactory(code=Branches.SPB, site_id=settings.SITE_ID)
    ad1, ad2, ad3 = AcademicDisciplineFactory.create_batch(3)
    client.login(CuratorFactory())
    params = dict(student_profile__year_of_admission=2011, student_profile__status="", branch=branch_spb,)
    students_1 = StudentFactory.create_batch(3, student_profile__academic_disciplines=[ad1, ad2], **params)
    students_2 = StudentFactory.create_batch(2, student_profile__academic_disciplines=[ad2, ad3], **params)
    students_3 = StudentFactory.create_batch(2, student_profile__academic_disciplines=[], **params)
    # Empty query
    response = client.get("{}?{}".format(search_url, "academic_disciplines="))
    assert response.json()["count"] == 0
    response = client.get("{}?academic_disciplines={}".format(search_url, ad1.pk))
    assert response.json()["count"] == len(students_1)
    assert {s.pk for s in students_1} == {r["user_id"] for r in response.json()["results"]}
    response = client.get(f"{search_url}?academic_disciplines={ad1.pk},{ad2.pk}")
    assert response.json()["count"] == len(students_1) + len(students_2)
    response = client.get(f"{search_url}?academic_disciplines={ad1.pk},{ad3.pk}")
    assert response.json()["count"] == len(students_1) + len(students_2)
    assert not {s.pk for s in students_3}.intersection({r["user_id"] for r in response.json()["results"]})


@pytest.mark.django_db
def test_student_search_by_year_of_admission(settings, client, search_url):
    client.login(CuratorFactory())
    branch_spb = BranchFactory(code=Branches.SPB, site_id=settings.SITE_ID)
    params = dict(student_profile__status="", branch=branch_spb,)
    students_1 = StudentFactory.create_batch(3, student_profile__year_of_admission=2011, **params)
    students_2 = StudentFactory.create_batch(2, student_profile__year_of_admission=2012, **params)
    students_3 = StudentFactory.create_batch(2, student_profile__year_of_admission=2013, **params)
    # Empty query
    response = client.get("{}?{}".format(search_url, "year_of_admission="))
    assert response.json()["count"] == 0
    response = client.get(f"{search_url}?year_of_admission={2011}")
    assert response.json()["count"] == len(students_1)
    assert {s.pk for s in students_1} == {r["user_id"] for r in response.json()["results"]}
    response = client.get(f"{search_url}?year_of_admission={2011},{2012}")
    assert response.json()["count"] == len(students_1) + len(students_2)
    response = client.get(f"{search_url}?year_of_admission={2013}")
    assert response.json()["count"] == len(students_3)
    assert {s.pk for s in students_3} == {r["user_id"] for r in response.json()["results"]}

