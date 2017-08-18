from __future__ import unicode_literals

import pytest
from django.urls import reverse

from learning.factories import CourseFactory, CourseOfferingFactory, \
    SemesterFactory, EnrollmentFactory
from learning.settings import PARTICIPANT_GROUPS, STUDENT_STATUS, SEMESTER_TYPES, \
    GRADES
from users.factories import StudentCenterFactory, StudentClubFactory, \
    UserFactory, VolunteerFactory

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
    assert response.status_code == 302
    client.login(curator)
    # Empty results by default
    response = client.get(SEARCH_URL)
    assert response.status_code == 200
    assert response.json()["total"] == 0
    response = client.get("{}?{}".format(SEARCH_URL, "curriculum_year=2011"))
    # Club users not included
    assert response.json()["total"] == 3
    # 2011 | 2012 years
    response = client.get("{}?{}".format(SEARCH_URL,
                                         "curriculum_year=2011%2C2012"))
    assert response.json()["total"] == 4
    # Now test groups filter
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={}".format(PARTICIPANT_GROUPS.MASTERS_DEGREE)
    ))
    assert response.json()["total"] == 0
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={}".format(PARTICIPANT_GROUPS.STUDENT_CENTER)
    ))
    assert response.json()["total"] == 2
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={}".format(PARTICIPANT_GROUPS.VOLUNTEER)
    ))
    assert response.json()["total"] == 1
    assert response.json()["users"][0]["first_name"] == volunteer.first_name
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups[]={}&groups[]={}".format(
            PARTICIPANT_GROUPS.STUDENT_CENTER,
            PARTICIPANT_GROUPS.VOLUNTEER
        )
    ))
    assert response.json()["total"] == 3
    volunteer.status = STUDENT_STATUS.expelled
    volunteer.save()
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups[]={}&groups[]={}&status={}".format(
            PARTICIPANT_GROUPS.STUDENT_CENTER,
            PARTICIPANT_GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled
        )
    ))
    assert response.json()["total"] == 1
    student.status = STUDENT_STATUS.reinstated
    student.save()
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups[]={}&groups[]={}&status={},{}".format(
            PARTICIPANT_GROUPS.STUDENT_CENTER,
            PARTICIPANT_GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled,
            STUDENT_STATUS.reinstated
        )
    ))
    assert response.json()["total"] == 2
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={},{}&status={},{}&{}".format(
            PARTICIPANT_GROUPS.STUDENT_CENTER,
            PARTICIPANT_GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled,
            STUDENT_STATUS.reinstated,
            "cnt_enrollments=2"
        )
    ))
    assert response.json()["total"] == 0
    # Check multi values still works for cnt_enrollments
    response = client.get("{}?{}".format(
        SEARCH_URL,
        "curriculum_year=2011&groups={},{}&status={},{}&{}".format(
            PARTICIPANT_GROUPS.STUDENT_CENTER,
            PARTICIPANT_GROUPS.VOLUNTEER,
            STUDENT_STATUS.expelled,
            STUDENT_STATUS.reinstated,
            "cnt_enrollments=0,2"
        )
    ))
    assert response.json()["total"] == 2


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
            PARTICIPANT_GROUPS.STUDENT_CENTER,
            PARTICIPANT_GROUPS.VOLUNTEER,
        )
    )
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["total"] == 0
    response = client.get(ENROLLMENTS_URL.format("0,2"))
    assert response.json()["total"] == 1
    s1 = SemesterFactory.create(year=2014, type=SEMESTER_TYPES.spring)
    s2 = SemesterFactory.create(year=2014, type=SEMESTER_TYPES.autumn)
    c1, c2 = CourseFactory.create_batch(2)
    co1 = CourseOfferingFactory.create(course=c1, semester=s1)
    co2 = CourseOfferingFactory.create(course=c1, semester=s2)
    e1 = EnrollmentFactory.create(student=student, course_offering=co1,
                                  grade=GRADES.good)
    e2 = EnrollmentFactory.create(student=student, course_offering=co2,
                                  grade=GRADES.not_graded)
    response = client.get(ENROLLMENTS_URL.format("1"))
    assert response.json()["total"] == 1
    e2.grade = GRADES.good
    response = client.get(ENROLLMENTS_URL.format("1"))
    assert response.json()["total"] == 1
    co3 = CourseOfferingFactory.create(course=c2)
    EnrollmentFactory.create(student=student, grade=GRADES.good,
                             course_offering=co3)
    response = client.get(ENROLLMENTS_URL.format("2"))
    assert response.json()["total"] == 1


# TODO: test when `expelled` and `studying` statuses set simultaneously in one query
# styding -> all statuses except `expelled`?
# TODO: test no group `GRADUATE_CENTER` if `studying` status set
