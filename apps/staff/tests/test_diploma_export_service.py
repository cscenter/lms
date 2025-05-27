"""
Tests for the ElectronicDiplomaExportService.
"""
import csv
import io
from unittest.mock import patch, MagicMock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from courses.constants import SemesterTypes
from courses.tests.factories import MetaCourseFactory, CourseFactory, SemesterFactory
from learning.settings import GradeTypes, StudentStatuses
from learning.tests.factories import EnrollmentFactory
from staff.services.diploma_export import ElectronicDiplomaExportService
from users.constants import GenderTypes
from users.models import StudentTypes
from users.tests.factories import (
    StudentProfileFactory, YandexUserDataFactory, SHADCourseRecordFactory
)


@pytest.mark.django_db
class TestElectronicDiplomaExportService:
    """Tests for the ElectronicDiplomaExportService."""

    def setup_method(self):
        """Set up test data."""
        # Set up common variables
        current_year = 2025
        self.graduated_year = current_year
        curriculum_year = current_year - 2

        # Create semester for the courses
        self.semester = SemesterFactory(year=curriculum_year, type=SemesterTypes.AUTUMN)

        # Create meta courses with indexes
        self.meta_course1 = MetaCourseFactory(index="CS101")
        self.meta_course2 = MetaCourseFactory(index="CS102")

        # Create a site object for testing
        from django.contrib.sites.models import Site
        self.site = Site.objects.create(domain='example.com', name='Test Site')

        # Create student profiles with Yandex data and user details
        self.student_profile1 = StudentProfileFactory(
            year_of_curriculum=curriculum_year,
            status=StudentStatuses.WILL_GRADUATE,  # Empty status means studying in progress
            year_of_admission=curriculum_year,
            type=StudentTypes.REGULAR,
            user__birth_date="2000-01-01",
            user__gender=GenderTypes.MALE,
            site=self.site,
            branch__site=self.site  # Ensure branch is associated with the same site
        )

        self.student_profile2 = StudentProfileFactory(
            year_of_curriculum=curriculum_year,
            status=StudentStatuses.WILL_GRADUATE,
            year_of_admission=curriculum_year,
            type=StudentTypes.REGULAR,
            user__birth_date="2000-02-02",
            user__gender=GenderTypes.FEMALE,
            site=self.site,
            branch__site=self.site  # Ensure branch is associated with the same site
        )

        # Create Yandex user data for the students
        self.yandex_data1 = YandexUserDataFactory(user=self.student_profile1.user)
        self.yandex_data2 = YandexUserDataFactory(user=self.student_profile2.user)

        # Create courses
        self.course1 = CourseFactory(
            meta_course=self.meta_course1,
            semester=self.semester,
            is_visible_in_certificates=True
        )
        self.course2 = CourseFactory(
            meta_course=self.meta_course2,
            semester=self.semester,
            is_visible_in_certificates=True
        )

        # Create enrollments with passing grades
        self.enrollment1 = EnrollmentFactory(
            course=self.course1,
            student_profile=self.student_profile1,
            grade=GradeTypes.GOOD
        )
        self.enrollment2 = EnrollmentFactory(
            course=self.course2,
            student_profile=self.student_profile1,
            grade=GradeTypes.EXCELLENT
        )
        self.enrollment3 = EnrollmentFactory(
            course=self.course1,
            student_profile=self.student_profile2,
            grade=GradeTypes.GOOD
        )

    def test_get_student_profiles(self):
        """Test the get_student_profiles method."""
        # Call the method
        student_profiles = ElectronicDiplomaExportService.get_student_profiles(
            self.site, self.graduated_year
        )

        # Check that the correct student profiles are returned
        assert len(student_profiles) == 2
        assert self.student_profile1 in student_profiles
        assert self.student_profile2 in student_profiles

    def test_get_meta_courses_data(self):
        """Test the get_meta_courses_data method."""
        # Get student profiles
        student_profiles = [self.student_profile1, self.student_profile2]

        # Set prefetched_enrollments on the user objects
        self.student_profile1.user.prefetched_enrollments = [
            self.enrollment1, self.enrollment2
        ]
        self.student_profile2.user.prefetched_enrollments = [
            self.enrollment3
        ]

        # Call the method
        meta_courses, courses_headers, header_to_index = ElectronicDiplomaExportService.get_meta_courses_data(
            student_profiles
        )

        # Check the meta courses
        assert len(meta_courses) == 2
        assert self.meta_course1.index in meta_courses
        assert self.meta_course2.index in meta_courses

        # Check the courses headers
        assert len(courses_headers) == 2
        assert f"{self.meta_course1.index}:evaluation" in courses_headers
        assert f"{self.meta_course2.index}:evaluation" in courses_headers

        # Check the header to index mapping
        assert len(header_to_index) == 2
        assert header_to_index[f"{self.meta_course1.index}:evaluation"] == self.meta_course1.index
        assert header_to_index[f"{self.meta_course2.index}:evaluation"] == self.meta_course2.index

    def test_prepare_student_data(self):
        """Test the prepare_student_data method."""
        # Get student profiles
        student_profiles = [self.student_profile1, self.student_profile2]

        # Set prefetched_enrollments on the user objects
        self.student_profile1.user.prefetched_enrollments = [
            self.enrollment1, self.enrollment2
        ]
        self.student_profile2.user.prefetched_enrollments = [
            self.enrollment3
        ]

        # Convert birth_date strings to datetime objects if they're strings
        import datetime
        if isinstance(self.student_profile1.user.birth_date, str):
            self.student_profile1.user.birth_date = datetime.datetime.strptime(self.student_profile1.user.birth_date, '%Y-%m-%d').date()
        if isinstance(self.student_profile2.user.birth_date, str):
            self.student_profile2.user.birth_date = datetime.datetime.strptime(self.student_profile2.user.birth_date, '%Y-%m-%d').date()

        # Get meta courses data
        meta_courses, _, _ = ElectronicDiplomaExportService.get_meta_courses_data(
            student_profiles
        )

        # Call the method
        student_data, courses_with_grades = ElectronicDiplomaExportService.prepare_student_data(
            student_profiles, meta_courses, self.graduated_year
        )

        # Check the student data
        assert len(student_data) == 2

        # Check the first student's data
        assert student_data[0]['base_data'][0] == self.yandex_data1.login
        assert student_data[0]['base_data'][1] == self.student_profile1.user.last_name
        assert student_data[0]['base_data'][2] == self.student_profile1.user.first_name

        # Check the second student's data
        assert student_data[1]['base_data'][0] == self.yandex_data2.login
        assert student_data[1]['base_data'][1] == self.student_profile2.user.last_name
        assert student_data[1]['base_data'][2] == self.student_profile2.user.first_name

        # Check the course results
        assert len(student_data[0]['course_results']) == 2
        assert len(student_data[1]['course_results']) == 1

        # Check the courses with grades
        assert len(courses_with_grades) == 2
        assert self.meta_course1.index in courses_with_grades
        assert self.meta_course2.index in courses_with_grades

    def test_create_csv_response(self):
        """Test the create_csv_response method."""
        # Get student profiles
        student_profiles = [self.student_profile1, self.student_profile2]

        # Set prefetched_enrollments on the user objects
        self.student_profile1.user.prefetched_enrollments = [
            self.enrollment1, self.enrollment2
        ]
        self.student_profile2.user.prefetched_enrollments = [
            self.enrollment3
        ]

        # Convert birth_date strings to datetime objects if they're strings
        import datetime
        if isinstance(self.student_profile1.user.birth_date, str):
            self.student_profile1.user.birth_date = datetime.datetime.strptime(self.student_profile1.user.birth_date, '%Y-%m-%d').date()
        if isinstance(self.student_profile2.user.birth_date, str):
            self.student_profile2.user.birth_date = datetime.datetime.strptime(self.student_profile2.user.birth_date, '%Y-%m-%d').date()

        # Get meta courses data
        meta_courses, courses_headers, header_to_index = ElectronicDiplomaExportService.get_meta_courses_data(
            student_profiles
        )

        # Get student data
        student_data, _ = ElectronicDiplomaExportService.prepare_student_data(
            student_profiles, meta_courses, self.graduated_year
        )

        # Call the method
        response = ElectronicDiplomaExportService.create_csv_response(
            student_data, courses_headers, header_to_index, self.graduated_year
        )

        # Check the response
        assert isinstance(response, HttpResponse)
        assert response['Content-Type'] == 'text/csv'
        assert f'attachment; filename="export_for_electronic_diplomas_{self.graduated_year}.csv"' in response['Content-Disposition']

        # Parse the CSV content
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Check the header row
        assert rows[0] == [
            'yauid', 'last_name', 'first_name', 'middle_name', 'birth_date',
            'snils', 'citizenship', 'sex', 'study_period_from', 'study_period_to',
            'number', 'issue_date', 'frdo_qual', 'control_mc_sum',
            f'{self.meta_course1.index}:evaluation',
            f'{self.meta_course2.index}:evaluation'
        ]

        # Check the data rows
        assert len(rows) == 3  # Header + 2 students

        # Check the first student's data
        assert rows[1][0] == self.yandex_data1.login
        assert rows[1][1] == self.student_profile1.user.last_name
        assert rows[1][2] == self.student_profile1.user.first_name

        # Check the second student's data
        assert rows[2][0] == self.yandex_data2.login
        assert rows[2][1] == self.student_profile2.user.last_name
        assert rows[2][2] == self.student_profile2.user.first_name

    def test_generate_export(self):
        """Test the generate_export method."""
        # Call the method
        with patch.object(ElectronicDiplomaExportService, 'get_student_profiles') as mock_get_student_profiles, \
             patch.object(ElectronicDiplomaExportService, 'get_meta_courses_data') as mock_get_meta_courses_data, \
             patch.object(ElectronicDiplomaExportService, 'prepare_student_data') as mock_prepare_student_data, \
             patch.object(ElectronicDiplomaExportService, 'create_csv_response') as mock_create_csv_response:

            # Set up the mocks
            mock_get_student_profiles.return_value = [self.student_profile1, self.student_profile2]
            mock_get_meta_courses_data.return_value = ({}, [], {})
            mock_prepare_student_data.return_value = ([], set())
            mock_create_csv_response.return_value = HttpResponse()

            # Call the method
            response = ElectronicDiplomaExportService.generate_export(
                self.site, self.graduated_year
            )

            # Check that the mocks were called with the correct arguments
            mock_get_student_profiles.assert_called_once_with(self.site, self.graduated_year)
            mock_get_meta_courses_data.assert_called_once_with(mock_get_student_profiles.return_value)
            mock_prepare_student_data.assert_called_once_with(
                mock_get_student_profiles.return_value,
                mock_get_meta_courses_data.return_value[0],
                self.graduated_year
            )
            mock_create_csv_response.assert_called_once_with(
                mock_prepare_student_data.return_value[0],
                mock_get_meta_courses_data.return_value[1],
                mock_get_meta_courses_data.return_value[2],
                self.graduated_year
            )

            # Check the response
            assert response == mock_create_csv_response.return_value
