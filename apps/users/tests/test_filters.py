import datetime

import pytest

from core.urls import reverse, reverse_lazy
from courses.settings import SemesterTypes
from courses.tests.factories import MetaCourseFactory, SemesterFactory, \
    CourseFactory
from learning.settings import StudentStatuses, GradeTypes
from learning.tests.factories import EnrollmentFactory, GraduateFactory
from users.constants import AcademicRoles
from users.tests.factories import StudentCenterFactory, StudentClubFactory, \
    UserFactory, VolunteerFactory, add_user_groups


@pytest.fixture(scope="module")
def search_url():
    return reverse_lazy('staff:student_search_json')


@pytest.mark.django_db
def test_student_search(client, curator, search_url):
    """Simple test cases to make sure, multi values still works"""
    # XXX: `name` filter not tested now due to postgres specific syntax
    student = StudentCenterFactory(enrollment_year=2011,
                                   status="",
                                   last_name='Иванов',
                                   first_name='Иван')
    StudentCenterFactory(enrollment_year=2011,
                         status="",
                         last_name='Иванов',
                         first_name='Иван')
    StudentCenterFactory(enrollment_year=2012,
                         status=StudentStatuses.EXPELLED,
                         last_name='Иванов',
                         first_name='Иван')
    StudentClubFactory(enrollment_year=2011,
                       last_name='Сидоров',
                       first_name='Сидор')
    volunteer = VolunteerFactory(enrollment_year=2011, status="")

    response = client.get(search_url)
    assert response.status_code == 403
    client.login(curator)
    # Empty results by default
    response = client.get(search_url)
    assert response.status_code == 200
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(search_url, "curriculum_year=2011"))
    # Club users not included
    assert response.json()["count"] == 3
    # 2011 | 2012 years
    response = client.get("{}?{}".format(search_url,
                                         "curriculum_year=2011%2C2012"))
    assert response.json()["count"] == 4
    # Now test groups filter
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups={}".format(AcademicRoles.MASTERS_DEGREE)
    ))
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups={}".format(AcademicRoles.STUDENT)
    ))
    assert response.json()["count"] == 2
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups={}".format(AcademicRoles.VOLUNTEER)
    ))
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["short_name"] == volunteer.get_short_name()
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups[]={}&groups[]={}".format(
            AcademicRoles.STUDENT,
            AcademicRoles.VOLUNTEER
        )
    ))
    assert response.json()["count"] == 3
    volunteer.status = StudentStatuses.EXPELLED
    volunteer.save()
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups[]={}&groups[]={}&status={}".format(
            AcademicRoles.STUDENT,
            AcademicRoles.VOLUNTEER,
            StudentStatuses.EXPELLED
        )
    ))
    assert response.json()["count"] == 1
    student.status = StudentStatuses.REINSTATED
    student.save()
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups[]={}&groups[]={}&status={},{}".format(
            AcademicRoles.STUDENT,
            AcademicRoles.VOLUNTEER,
            StudentStatuses.EXPELLED,
            StudentStatuses.REINSTATED
        )
    ))
    assert response.json()["count"] == 2
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups={},{}&status={},{}&{}".format(
            AcademicRoles.STUDENT,
            AcademicRoles.VOLUNTEER,
            StudentStatuses.EXPELLED,
            StudentStatuses.REINSTATED,
            "cnt_enrollments=2"
        )
    ))
    assert response.json()["count"] == 0
    # Check multi values still works for cnt_enrollments
    response = client.get("{}?{}".format(
        search_url,
        "curriculum_year=2011&groups={},{}&status={},{}&{}".format(
            AcademicRoles.STUDENT,
            AcademicRoles.VOLUNTEER,
            StudentStatuses.EXPELLED,
            StudentStatuses.REINSTATED,
            "cnt_enrollments=0,2"
        )
    ))
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_student_search_enrollments(client, curator, search_url):
    """
    Count successfully passed courses instead of course_offerings.
    """
    client.login(curator)
    student = StudentCenterFactory(curriculum_year=2011, status="",
                                   last_name='Иванов', first_name='Иван')
    ENROLLMENTS_URL = "{}?{}".format(
        search_url,
        "curriculum_year=2011&groups={},{}&cnt_enrollments={{}}".format(
            AcademicRoles.STUDENT,
            AcademicRoles.VOLUNTEER,
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
    other_student = StudentCenterFactory(curriculum_year=2011)
    e3 = EnrollmentFactory.create(student=other_student, grade=GradeTypes.GOOD)
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 1
    response = client.get(ENROLLMENTS_URL.format("1,2"))
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_student_search_by_groups(client, curator, search_url):
    from users.filters import UserFilter
    client.login(curator)
    # All users below are considered as `studying` due to empty status
    club_students = StudentClubFactory.create_batch(2)
    students = StudentCenterFactory.create_batch(3, enrollment_year=2011,
                                                 status="", city_id='spb')
    volunteers = VolunteerFactory.create_batch(4, enrollment_year=2011,
                                               status="", city_id='spb')
    # Empty results if no query provided
    response = client.get(search_url)
    assert response.json()["count"] == 0
    # And without any value it still empty
    response = client.get("{}?{}".format(search_url, "groups="))
    assert response.json()["count"] == 0
    # With any non-empty query field we filter by predefined
    # set of UserFilter.FILTERING_GROUPS
    response = client.get("{}?{}".format(search_url, "status=studying&groups="))
    json_data = response.json()
    assert json_data["count"] == len(students) + len(volunteers)
    url_show_club_students = "{}?{}".format(
        search_url, "groups={}".format(AcademicRoles.STUDENT_CLUB))
    response = client.get(url_show_club_students)
    json_data = response.json()
    assert AcademicRoles.STUDENT_CLUB not in UserFilter.FILTERING_GROUPS
    # Since club group not in predefined list - this is an empty query
    pytest.xfail(reason='Groups are not restricted right now. '
                        'Struggling with django_filters')
    assert json_data["count"] == 0


@pytest.mark.django_db
def test_student_search_by_city(client, curator, search_url):
    client.login(curator)
    _ = UserFactory.create(city_id='spb')  # random user
    students_spb = StudentCenterFactory.create_batch(3,
        enrollment_year=2011, status="", city_id='spb')
    students_nsk = StudentCenterFactory.create_batch(2,
        enrollment_year=2011, status="", city_id='nsk')
    # Send empty query
    response = client.get("{}?{}".format(search_url, "cities="))
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(search_url, "cities=spb"))
    json_data = response.json()
    assert json_data["count"] == len(students_spb)
    assert {s.pk for s in students_spb} == {r["pk"] for r in json_data["results"]}
    response = client.get("{}?{}".format(search_url, "cities=spb,nsk"))
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)
    # Test another query format supported by Django
    response = client.get("{}?{}".format(search_url, "cities[]=spb&cities[]=nsk"))
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)
    # All with status `studying`
    response = client.get("{}?{}".format(search_url, "status=studying&cities="))
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)


@pytest.mark.django_db
def test_student_by_virtual_status_studying(client, curator, search_url):
    client.login(curator)
    students_spb = StudentCenterFactory.create_batch(4,
        enrollment_year=2011, status="", city_id='spb')
    students_nsk = StudentCenterFactory.create_batch(7,
        enrollment_year=2011, status="", city_id='nsk')
    volunteers = VolunteerFactory.create_batch(
        3, enrollment_year=2011, status="", city_id='spb')
    graduated_on = datetime.date(year=2017, month=1, day=1)
    graduated = GraduateFactory.create_batch(
        5, city_id='spb', status='', enrollment_year=2011,
        graduate_profile__graduated_on=graduated_on)
    response = client.get("{}?{}".format(search_url, "status=studying"))
    json_data = response.json()
    total_studying = len(students_spb) + len(students_nsk) + len(volunteers)
    assert json_data["count"] == total_studying
    expelled = StudentCenterFactory.create_batch(
        2, enrollment_year=2011, status="expelled", city_id='spb')
    # If no groups specified - `GRADUATE_CENTER` group excluded from results
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
        search_url, "status=studying&groups={}".format(AcademicRoles.VOLUNTEER))
    response = client.get(url)
    assert response.json()["count"] == len(volunteers)
    # Edge case - show `studying` among graduated
    query = "status=studying&groups={}".format(AcademicRoles.GRADUATE_CENTER)
    response = client.get("{}?{}".format(search_url, query))
    assert response.json()["count"] == 0
    # If some group added except graduate group - concat results
    query = "status=studying&groups={},{}".format(AcademicRoles.VOLUNTEER,
                                                  AcademicRoles.GRADUATE_CENTER)
    response = client.get("{}?{}".format(search_url, query))
    assert response.json()["count"] == len(volunteers) + len(graduated)
    # Edge case #2 - graduate can have `master` subgroup
    add_user_groups(graduated[0], [AcademicRoles.MASTERS_DEGREE])
    query = "status=studying&groups={},{}".format(AcademicRoles.GRADUATE_CENTER,
                                                  AcademicRoles.MASTERS_DEGREE)
    response = client.get("{}?{}".format(search_url, query))
    assert response.json()["count"] == len(graduated)

