import re

import pytest
from bs4 import BeautifulSoup

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils import timezone

from core.urls import reverse
from courses.tests.factories import CourseFactory, MetaCourseFactory, SemesterFactory
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from users.models import CertificateOfParticipation
from users.tests.factories import (
    CertificateOfParticipationFactory, CuratorFactory, StudentFactory,
    StudentProfileFactory
)


@pytest.mark.django_db
def test_create_reference(client, assert_redirect):
    """
       Check redirect to student's #for-curator-tab after form submit
       Check that student name on english is used instead of russian
        in the english version of reference.
       Note: signature is used as student name in english reference versions.
    """
    curator = CuratorFactory()
    client.login(curator)

    student_profile = StudentProfileFactory()
    SemesterFactory.create_batch(2, year=timezone.now().year)
    form_url = reverse('student_reference_add',
                       subdomain=settings.LMS_SUBDOMAIN,
                       kwargs={"user_id": student_profile.user_id})
    note = 'Some note'
    student_name_on_english = 'Student name on english'
    form_data = {
        'note': note,
        'signature': student_name_on_english
    }
    response = client.post(form_url, form_data)
    assert CertificateOfParticipation.objects.count() == 1
    ref = CertificateOfParticipation.objects.first()
    expected_url = f"{student_profile.user.get_absolute_url()}#for-curator-tab"
    assert_redirect(response, expected_url)

    url_ru_courses = f"{ref.get_absolute_url()}?style=shad_ru_with_courses"
    url_ru_without_courses = f"{ref.get_absolute_url()}?style=shad_ru_without_courses"
    url_en_courses = f"{ref.get_absolute_url()}?style=shad_en_with_courses"
    url_en_graduated = f"{ref.get_absolute_url()}?style=shad_en_without_courses"

    html = client.get(url_ru_courses).content.decode('utf-8')
    assert note in html
    assert student_name_on_english not in html
    assert student_profile.user.get_full_name() in html

    html = client.get(url_ru_without_courses).content.decode('utf-8')
    assert note in html
    assert student_name_on_english not in html
    assert student_profile.user.get_full_name() in html

    html = client.get(url_en_courses).content.decode('utf-8')
    assert note in html
    assert student_name_on_english in html
    assert student_profile.user.get_full_name() not in html

    html = client.get(url_en_graduated).content.decode('utf-8')
    assert note in html
    assert student_name_on_english in html
    assert student_profile.user.get_full_name() not in html


@pytest.mark.django_db
def test_user_detail_view(client):
    """Show reference-add button only to curators (superusers)"""
    # check user page without curator credentials
    student = StudentFactory()
    client.login(student)
    response = client.get(student.get_absolute_url())
    soup = BeautifulSoup(response.content, "html.parser")
    button = soup.find('a', text=_("Create reference"))
    assert button is None
    # Login with curator credentials
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(student.get_absolute_url())
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    button = soup.find(string=re.compile(_("Create reference")))
    assert button is not None


@pytest.mark.django_db
def test_user_detail_reference_list_view(client):
    """Check reference list appears on student profile page"""
    curator = CuratorFactory()
    client.login(curator)
    student_profile = StudentProfileFactory()
    EnrollmentFactory()
    CertificateOfParticipationFactory(student_profile=student_profile)
    student_detail_url = student_profile.user.get_absolute_url()
    response = client.get(student_detail_url)
    soup = BeautifulSoup(response.content, "html.parser")
    list_header = soup.find('h4', text=re.compile(_("Student references")))
    assert list_header is not None
    client.login(student_profile.user)
    response = client.get(student_detail_url)
    soup = BeautifulSoup(response.content, "html.parser")
    list_header = soup.find('h4', text=_("Student references"))
    assert list_header is None


@pytest.mark.django_db
def test_reference_detail(client, assert_login_redirect, settings):
    """Check enrollments duplicates, reference fields"""
    student = StudentFactory()
    # add 2 enrollments from 1 course reading exactly
    meta_course = MetaCourseFactory.create()
    semesters = SemesterFactory.create_batch(2, year=timezone.now().year)
    enrollments = []
    student_profile = student.get_student_profile(settings.SITE_ID)
    for s in semesters:
        e = EnrollmentFactory(
            course=CourseFactory(meta_course=meta_course, semester=s),
            student=student_profile.user,
            student_profile=student_profile,
            grade=GradeTypes.GOOD
        )
        enrollments.append(e)
    reference = CertificateOfParticipationFactory(
        student_profile=student_profile,
        note="TEST",
        signature="SIGNATURE")
    url = reference.get_absolute_url() + "?style=shad_en_with_courses"
    client.login(student)
    response = client.get(url)
    assert response.status_code == 403
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(url)
    assert response.context['certificate_of_participation'].note == "TEST"
    soup = BeautifulSoup(response.content, "html.parser")
    sig_text = soup.find(text=re.compile('SIGNATURE'))
    assert sig_text is not None
    es = soup.find(id='reference-yds-page-body').findAll('td')
    expected_enrollments_count = 1
    assert len(es) / 3 == expected_enrollments_count


@pytest.mark.django_db
def test_certificate_of_participant_hidden_course(client):
    student = StudentFactory()
    curator = CuratorFactory()
    semesters = SemesterFactory.create_batch(2, year=timezone.now().year)
    course = CourseFactory(semester=semesters[1])
    student_profile = student.get_student_profile(settings.SITE_ID)
    EnrollmentFactory(
        course=course,
        student=student_profile.user,
        student_profile=student_profile,
        grade=GradeTypes.GOOD
    )
    reference = CertificateOfParticipationFactory(
        student_profile=student_profile,
        signature="English Student Name"
    )
    url = reference.get_absolute_url() + "?style=shad_ru_with_courses"
    client.login(curator)

    response = client.get(url)
    data = response.content.decode('utf-8')
    assert course.name in data

    course.is_visible_in_certificates = False
    course.save()
    response = client.get(url)
    data = response.content.decode('utf-8')
    assert course.name not in data
