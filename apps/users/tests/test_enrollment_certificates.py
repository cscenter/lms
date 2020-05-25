import re

import factory
import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.translation import ugettext as _

from core.urls import reverse
from courses.tests.factories import MetaCourseFactory, SemesterFactory, \
    CourseFactory
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from users.models import EnrollmentCertificate
from users.tests.factories import UserFactory, \
    CertificateOfParticipationFactory, \
    StudentFactory, CuratorFactory, StudentProfileFactory


@pytest.mark.django_db
def test_create_reference(client, assert_redirect):
    """Check FIO substitute in signature input field
       Check redirect to reference detail after form submit
    """
    curator = CuratorFactory()
    client.login(curator)
    student_profile = StudentProfileFactory()
    form_url = reverse('student_reference_add',
                       subdomain=settings.LMS_SUBDOMAIN,
                       args=[student_profile.id])
    response = client.get(form_url)
    soup = BeautifulSoup(response.content, "html.parser")
    sig_input = soup.find(id="id_signature")
    assert sig_input.attrs.get('value') == curator.get_full_name()

    student_profile = StudentProfileFactory()
    form_url = reverse('student_reference_add',
                       subdomain=settings.LMS_SUBDOMAIN,
                       args=[student_profile.id])
    form_data = {
        'note': '',
        'signature': 'admin'
    }
    response = client.post(form_url, form_data)
    assert EnrollmentCertificate.objects.count() == 1
    ref = EnrollmentCertificate.objects.first()
    expected_url = ref.get_absolute_url()
    assert_redirect(response, expected_url)


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
    """Check reference list appears on student profile page for curators only"""
    student = StudentFactory()
    EnrollmentFactory()
    CertificateOfParticipationFactory(student=student)
    curator = CuratorFactory()
    url = student.get_absolute_url()
    client.login(curator)
    response = client.get(url)
    assert response.context['profile_user'].enrollment_certificates.count() == 1
    soup = BeautifulSoup(response.content, "html.parser")
    list_header = soup.find('h4', text=re.compile(_("Student references")))
    assert list_header is not None
    client.login(student)
    response = client.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    list_header = soup.find('h4', text=_("Student references"))
    assert list_header is None


@pytest.mark.django_db
def test_reference_detail(client, assert_login_redirect, settings):
    """Check enrollments duplicates, reference fields"""
    student = StudentFactory()
    # add 2 enrollments from 1 course reading exactly
    meta_course = MetaCourseFactory.create()
    semesters = SemesterFactory.create_batch(2, year=2014)
    enrollments = []
    for s in semesters:
        e = EnrollmentFactory(
            course=CourseFactory(meta_course=meta_course, semester=s),
            student=student,
            grade=GradeTypes.GOOD
        )
        enrollments.append(e)
    reference = CertificateOfParticipationFactory(
        student_profile=student.get_student_profile(settings.SITE_ID),
        note="TEST",
        signature="SIGNATURE")
    url = reference.get_absolute_url()
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
    es = soup.find(id='reference-page-body').findAll('li')
    expected_enrollments_count = 1
    assert len(es) == expected_enrollments_count

