import re

import factory
import pytest
from bs4 import BeautifulSoup
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _

from core.tests.utils import CSCTestCase
from core.urls import reverse
from courses.tests.factories import MetaCourseFactory, SemesterFactory, \
    CourseFactory
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from learning.tests.mixins import MyUtilitiesMixin
from users.constants import AcademicRoles
from users.models import User, EnrollmentCertificate
from users.tests.factories import UserFactory, EnrollmentCertificateFactory, \
    StudentCenterFactory, add_user_groups, StudentClubFactory


@pytest.mark.django_db
def test_create_reference(client, assert_redirect):
    """Check FIO substitute in signature input field
       Check redirect to reference detail after form submit
    """
    user_data = factory.build(dict, FACTORY_CLASS=UserFactory)
    user = User.objects.create_user(**user_data)
    UserFactory.reset_sequence(1)
    curator = UserFactory(is_superuser=True, is_staff=True)
    client.login(curator)
    form_url = reverse('user_reference_add', args=[user.id])
    response = client.get(form_url)
    soup = BeautifulSoup(response.content, "html.parser")
    sig_input = soup.find(id="id_signature")
    assert sig_input.attrs.get('value') == curator.get_full_name()

    student = StudentCenterFactory()
    form_url = reverse('user_reference_add', args=[student.id])
    form_data = factory.build(dict, FACTORY_CLASS=EnrollmentCertificateFactory)
    response = client.post(form_url, form_data)
    assert EnrollmentCertificate.objects.count() == 1
    ref = EnrollmentCertificate.objects.first()
    expected_url = ref.get_absolute_url()
    assert_redirect(response, expected_url)


class EnrollmentCertificateTests(MyUtilitiesMixin, CSCTestCase):
    def test_user_detail_view(self):
        """Show reference-add button only to curators (superusers)"""
        # check user page without curator credentials
        student = UserFactory.create(groups=[AcademicRoles.STUDENT],
                                     enrollment_year=2011)
        self.doLogin(student)
        url = reverse('user_detail', args=[student.pk])
        response = self.client.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        button = soup.find('a', text=_("Create reference"))
        self.assertIsNone(button)
        # check with curator credentials
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        self.doLogin(curator)
        response = self.client.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        button = soup.find(string=re.compile(_("Create reference")))
        self.assertIsNotNone(button)

    def test_user_detail_reference_list_view(self):
        """Check reference list appears on student profile page for curators only"""
        student = StudentCenterFactory()
        EnrollmentFactory.create()
        EnrollmentCertificateFactory.create(student=student)
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        url = reverse('user_detail', args=[student.pk])
        self.doLogin(curator)
        response = self.client.get(url)
        self.assertEqual(
            response.context['profile_user'].enrollment_certificates.count(), 1)
        soup = BeautifulSoup(response.content, "html.parser")
        list_header = soup.find('h4', text=re.compile(_("Student references")))
        self.assertIsNotNone(list_header)
        self.doLogin(student)
        response = self.client.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        list_header = soup.find('h4', text=_("Student references"))
        self.assertIsNone(list_header)

    def test_reference_detail(self):
        """Check enrollments duplicates, reference fields"""
        student = StudentCenterFactory()
        # add 2 enrollments from 1 course reading exactly
        meta_course = MetaCourseFactory.create()
        semesters = SemesterFactory.create_batch(2, year=2014)
        enrollments = []
        for s in semesters:
            e = EnrollmentFactory.create(
                course=CourseFactory.create(
                    meta_course=meta_course,
                    semester=s),
                student=student,
                grade=GradeTypes.GOOD
            )
            enrollments.append(e)
        reference = EnrollmentCertificateFactory.create(
            student=student,
            note="TEST",
            signature="SIGNATURE")
        url = reference.get_absolute_url()
        self.doLogin(student)
        self.assertLoginRedirect(url)
        curator = UserFactory.create(is_superuser=True, is_staff=True)
        self.doLogin(curator)
        response = self.client.get(url)
        self.assertEqual(response.context['object'].note, "TEST")
        soup = BeautifulSoup(response.content, "html.parser")
        sig_text = soup.find(text=re.compile('SIGNATURE'))
        self.assertIsNotNone(sig_text)
        es = soup.find(id='reference-page-body').findAll('li')
        expected_enrollments_count = 1
        self.assertEqual(len(es), expected_enrollments_count)

    def test_club_student_login_on_cscenter_site(self):
        club_student = StudentClubFactory()
        self.doLogin(club_student)
        login_data = {
            'username': club_student.username,
            'password': club_student.raw_password
        }
        response = self.client.post(reverse('login'), login_data)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        # can't login message in __all__
        self.assertIn("__all__", form.errors)
        add_user_groups(club_student, [User.roles.STUDENT])
        club_student.save()
        response = self.client.post(reverse('login'), login_data)
        self.assertEqual(response.status_code, 302)
