import pytest
from django.urls import reverse

from learning.factories import MetaCourseFactory, CourseFactory, \
    SemesterFactory, EnrollmentFactory
from learning.settings import PARTICIPANT_GROUPS as GROUPS, STUDENT_STATUS, \
    GRADES, SemesterTypes
from users.factories import StudentCenterFactory, StudentClubFactory, \
    UserFactory, VolunteerFactory, GraduateFactory

SEARCH_URL = reverse('staff:student_search_json')


@pytest.mark.django_db
def test_student_search(client, curator):
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
                         status=STUDENT_STATUS.expelled,
                         last_name='Иванов',
                         first_name='Иван')
    StudentClubFactory(enrollment_year=2011,
                       last_name='Сидоров',
                       first_name='Сидор')
    volunteer = VolunteerFactory(enrollment_year=2011, status="")

    response = client.get(SEARCH_URL)
    assert response.status_code == 403
    client.login(curator)
    # Empty results by default
    response = client.get(SEARCH_URL)
    assert response.status_code == 200
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(SEARCH_URL, "curriculum_year=2011"))
    # Club users not included
    assert response.json()["count"] == 3
    # 2011 | 2012 years
    response = client.get("{}?{}".format(SEARCH_URL,
                                         "curriculum_year=2011%2C2012"))
    assert response.json()["count"] == 4
    # Now test groups filter
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={}".format(GROUPS.MASTERS_DEGREE)
    ))
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={}".format(GROUPS.STUDENT_CENTER)
    ))
    assert response.json()["count"] == 2
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={}".format(GROUPS.VOLUNTEER)
    ))
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["short_name"] == volunteer.get_short_name()
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups[]={}&groups[]={}".format(
            GROUPS.STUDENT_CENTER,
            GROUPS.VOLUNTEER
        )
    ))
    assert response.json()["count"] == 3
    volunteer.status = STUDENT_STATUS.expelled
    volunteer.save()
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups[]={}&groups[]={}&status={}".format(
            GROUPS.STUDENT_CENTER,
            GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled
        )
    ))
    assert response.json()["count"] == 1
    student.status = STUDENT_STATUS.reinstated
    student.save()
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups[]={}&groups[]={}&status={},{}".format(
            GROUPS.STUDENT_CENTER,
            GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled,
            STUDENT_STATUS.reinstated
        )
    ))
    assert response.json()["count"] == 2
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={},{}&status={},{}&{}".format(
            GROUPS.STUDENT_CENTER,
            GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled,
            STUDENT_STATUS.reinstated,
            "cnt_enrollments=2"
        )
    ))
    assert response.json()["count"] == 0
    # Check multi values still works for cnt_enrollments
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={},{}&status={},{}&{}".format(
            GROUPS.STUDENT_CENTER,
            GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled,
            STUDENT_STATUS.reinstated,
            "cnt_enrollments=0,2"
        )
    ))
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_student_search_enrollments(client, curator):
    """
    Count successfully passed courses instead of course_offerings.
    """
    client.login(curator)
    student = StudentCenterFactory(curriculum_year=2011, status="",
                                   last_name='Иванов', first_name='Иван')
    ENROLLMENTS_URL = "{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={},{}&cnt_enrollments={{}}".format(
            GROUPS.STUDENT_CENTER,
            GROUPS.VOLUNTEER,
        )
    )
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 0
    response = client.get(ENROLLMENTS_URL.format("0,2"))
    assert response.json()["count"] == 1
    s1 = SemesterFactory.create(year=2014, type=SemesterTypes.spring)
    s2 = SemesterFactory.create(year=2014, type=SemesterTypes.autumn)
    mc1, mc2 = MetaCourseFactory.create_batch(2)
    co1 = CourseFactory.create(meta_course=mc1, semester=s1)
    co2 = CourseFactory.create(meta_course=mc1, semester=s2)
    e1 = EnrollmentFactory.create(student=student, course=co1,
                                  grade=GRADES.good)
    e2 = EnrollmentFactory.create(student=student, course=co2,
                                  grade=GRADES.not_graded)
    response = client.get(ENROLLMENTS_URL.format("1"))
    assert response.json()["count"] == 1
    e2.grade = GRADES.good
    e2.save()
    response = client.get(ENROLLMENTS_URL.format("1"))
    assert response.json()["count"] == 1
    co3 = CourseFactory.create(meta_course=mc2)
    EnrollmentFactory.create(student=student, grade=GRADES.good, course=co3)
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 1
    other_student = StudentCenterFactory(curriculum_year=2011)
    e3 = EnrollmentFactory.create(student=other_student, grade=GRADES.good)
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["count"] == 1
    response = client.get(ENROLLMENTS_URL.format("1,2"))
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_student_search_by_groups(client, curator):
    from users.filters import UserFilter
    client.login(curator)
    # All users below are considered as `studying` due to empty status
    club_students = StudentClubFactory.create_batch(2)
    students = StudentCenterFactory.create_batch(3, enrollment_year=2011,
                                                 status="", city_id='spb')
    volunteers = VolunteerFactory.create_batch(4, enrollment_year=2011,
                                               status="", city_id='spb')
    # Empty results if no query provided
    response = client.get(SEARCH_URL)
    assert response.json()["count"] == 0
    # And without any value it still empty
    response = client.get("{}?{}".format(SEARCH_URL, "groups="))
    assert response.json()["count"] == 0
    # With any non-empty query field we filter by predefined
    # set of UserFilter.FILTERING_GROUPS
    response = client.get("{}?{}".format(SEARCH_URL, "status=studying&groups="))
    json_data = response.json()
    assert json_data["count"] == len(students) + len(volunteers)
    url_show_club_students = "{}?{}".format(
        SEARCH_URL, "groups={}".format(GROUPS.STUDENT_CLUB))
    response = client.get(url_show_club_students)
    json_data = response.json()
    assert GROUPS.STUDENT_CLUB not in UserFilter.FILTERING_GROUPS
    # Since club group not in predefined list - this is an empty query
    pytest.xfail(reason='Groups are not restricted right now. '
                        'Struggling with django_filters')
    assert json_data["count"] == 0


@pytest.mark.django_db
def test_student_search_by_city(client, curator):
    client.login(curator)
    _ = UserFactory.create(city_id='spb')  # random user
    students_spb = StudentCenterFactory.create_batch(3,
        enrollment_year=2011, status="", city_id='spb')
    students_nsk = StudentCenterFactory.create_batch(2,
        enrollment_year=2011, status="", city_id='nsk')
    # Send empty query
    response = client.get("{}?{}".format(SEARCH_URL, "cities="))
    assert response.json()["count"] == 0
    response = client.get("{}?{}".format(SEARCH_URL, "cities=spb"))
    json_data = response.json()
    assert json_data["count"] == len(students_spb)
    assert {s.pk for s in students_spb} == {r["pk"] for r in json_data["results"]}
    response = client.get("{}?{}".format(SEARCH_URL, "cities=spb,nsk"))
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)
    # Test another query format supported by Django
    response = client.get("{}?{}".format(SEARCH_URL, "cities[]=spb&cities[]=nsk"))
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)
    # All with status `studying`
    response = client.get("{}?{}".format(SEARCH_URL, "status=studying&cities="))
    json_data = response.json()
    assert json_data["count"] == len(students_spb) + len(students_nsk)


@pytest.mark.django_db
def test_student_by_virtual_status_studying(client, curator):
    client.login(curator)
    students_spb = StudentCenterFactory.create_batch(4,
        enrollment_year=2011, status="", city_id='spb')
    students_nsk = StudentCenterFactory.create_batch(7,
        enrollment_year=2011, status="", city_id='nsk')
    volunteers = VolunteerFactory.create_batch(
        3, enrollment_year=2011, status="", city_id='spb')
    graduated = GraduateFactory.create_batch(
        5, city_id='spb', status='', enrollment_year=2011, graduation_year=2017)
    response = client.get("{}?{}".format(SEARCH_URL, "status=studying"))
    json_data = response.json()
    total_studying = len(students_spb) + len(students_nsk) + len(volunteers)
    assert json_data["count"] == total_studying
    expelled = StudentCenterFactory.create_batch(
        2, enrollment_year=2011, status="expelled", city_id='spb')
    # If no groups specified - `GRADUATE_CENTER` group excluded from results
    response = client.get("{}?{}".format(SEARCH_URL, "status=studying"))
    json_data = response.json()
    assert json_data["count"] == total_studying
    # Test `studying` includes `will_graduate` and `reinstated` statuses
    response = client.get("{}?{}".format(SEARCH_URL,
                                         "status=studying,will_graduate"))
    assert response.json()["count"] == total_studying
    url = "{}?{}".format(SEARCH_URL, "status=studying,will_graduate,reinstated")
    response = client.get(url)
    assert response.json()["count"] == total_studying
    # More precisely by group
    url = "{}?{}".format(
        SEARCH_URL, "status=studying&groups={}".format(GROUPS.VOLUNTEER))
    response = client.get(url)
    assert response.json()["count"] == len(volunteers)
    # Edge case - show `studying` among graduated
    query = "status=studying&groups={}".format(GROUPS.GRADUATE_CENTER)
    response = client.get("{}?{}".format(SEARCH_URL, query))
    assert response.json()["count"] == 0
    # If some group added except graduate group - concat results
    query = "status=studying&groups={},{}".format(GROUPS.VOLUNTEER,
                                                  GROUPS.GRADUATE_CENTER)
    response = client.get("{}?{}".format(SEARCH_URL, query))
    assert response.json()["count"] == len(volunteers) + len(graduated)
    # Edge case #2 - graduate can have `master` subgroup
    graduated[0].groups.add(GROUPS.MASTERS_DEGREE)
    query = "status=studying&groups={},{}".format(GROUPS.GRADUATE_CENTER,
                                                  GROUPS.MASTERS_DEGREE)
    response = client.get("{}?{}".format(SEARCH_URL, query))
    assert response.json()["count"] == len(graduated)

