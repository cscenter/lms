"""
Services for diploma export functionality.
"""
import csv
import datetime
from typing import Dict, List, Set, Tuple, Any, Iterable

from django.http import HttpResponse
from django.db.models import Prefetch, QuerySet

from courses.models import MetaCourse
from learning.models import Enrollment
from learning.settings import GradeTypes, StudentStatuses
from users.constants import GenderTypes
from users.models import StudentProfile, SHADCourseRecord, StudentTypes


class ElectronicDiplomaExportService:
    """
    Service for exporting student data for electronic diplomas.

    This service handles the preparation and export of student data for electronic diplomas,
    including personal information and course grades.
    """

    @staticmethod
    def get_student_profiles(site, graduated_year: int) -> QuerySet:
        """
        Get student profiles for electronic diplomas export with optimized prefetching.
        """

        return StudentProfile.objects.filter(
            site_id=site.id,
            type=StudentTypes.REGULAR,
            status=StudentStatuses.WILL_GRADUATE,
            year_of_admission__in=[graduated_year-1, graduated_year-2, graduated_year-3, graduated_year-4]
        ).select_related(
            'user',
            'branch',
            'user__yandex_data'
        ).prefetch_related(
            Prefetch(
                'user__shadcourserecord_set',
                queryset=SHADCourseRecord.objects.select_related('semester'),
            ),
            'user__onlinecourserecord_set',
            Prefetch(
                'user__enrollment_set',
                queryset=Enrollment.objects.filter(
                    is_deleted=False,
                    grade__in=GradeTypes.satisfactory_grades
                ).select_related('course', 'course__meta_course'),
                to_attr='prefetched_enrollments'
            ),
            # Prefetch academic_discipline as it's a many-to-many relationship
            'academic_disciplines'
        )

    @staticmethod
    def get_meta_courses_data(student_profiles: Iterable[StudentProfile]) -> Tuple[Dict[str, str], List[str], Dict[str, str]]:
        """
        Get meta courses data and generate headers for CSV export.
        """
        # Collect all meta course IDs from student enrollments
        meta_course_ids = {
            enrollment.course.meta_course_id
            for profile in student_profiles
            for enrollment in getattr(profile.user, 'prefetched_enrollments', [])
            if any(e.course.is_visible_in_certificates for e in getattr(profile.user, 'prefetched_enrollments', [])
                if e.course.meta_course_id == enrollment.course.meta_course_id)
        }

        meta_courses = []
        courses_headers = []
        header_to_index = {}

        # Get meta courses and create headers
        for mc in MetaCourse.objects.filter(id__in=meta_course_ids):
            meta_courses.append(mc.index)

            # Generate header and add to headers list
            header = f"{mc.index}:evaluation"
            courses_headers.append(header)
            header_to_index[header] = mc.index

        return meta_courses, courses_headers, header_to_index

    @staticmethod
    def prepare_student_data(student_profiles: Iterable[StudentProfile], meta_courses: Dict[str, str],
                            graduated_year: int) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """
        Prepare student data for CSV export.
        """
        courses_with_grades = set()
        student_data = []

        for profile in student_profiles:
            user = profile.user

            # Get courses with grades for this student
            course_results = profile.get_courses_grades(meta_courses)
            courses_with_grades.update(course_results.keys())

            # Prepare base data for the student
            base_data = [
                user.yandex_login,
                user.last_name,
                user.first_name,
                user.patronymic,
                user.birth_date.strftime('%Y-%m-%d') if user.birth_date and not isinstance(user.birth_date, str) else user.birth_date if isinstance(user.birth_date, str) else '',
                profile.snils,
                user.citizenship,
                GenderTypes.values[user.gender] if user.gender else "",
                datetime.datetime(profile.year_of_admission, 9, 1).strftime('%Y-%m-%d'),
                datetime.datetime(graduated_year, 5, 31).strftime('%Y-%m-%d'),
                profile.diploma_number,
                '',
                profile.academic_discipline if profile.academic_discipline else '',
                profile.get_passed_courses_total(),
            ]

            student_data.append({
                'base_data': base_data,
                'course_results': course_results
            })

        return student_data, courses_with_grades

    @staticmethod
    def create_csv_response(student_data: List[Dict[str, Any]], courses_headers: List[str],
                           header_to_index: Dict[str, str], graduated_year: int) -> HttpResponse:
        """
        Create CSV response with student data.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="export_for_electronic_diplomas_{graduated_year}.csv"'

        writer = csv.writer(response)

        # Write header row
        writer.writerow([
            'yauid', 'last_name', 'first_name', 'middle_name', 'birth_date',
            'snils', 'citizenship', 'sex', 'study_period_from', 'study_period_to',
            'number', 'issue_date', 'frdo_qual', 'control_mc_sum', *courses_headers
        ])

        # Write data for each student
        for data in student_data:
            row_data = data['base_data'].copy()
            course_results = data['course_results']

            # Add grades for each course in the headers
            for header in courses_headers:
                course_index = header_to_index[header]
                grade = course_results.get(course_index, "")
                row_data.append(grade.lower())

            writer.writerow(row_data)

        return response

    @classmethod
    def generate_export(cls, site, graduated_year: int) -> HttpResponse:
        """
        Generate CSV export for electronic diplomas.
        """
        # Get student profiles with optimized prefetching
        student_profiles = cls.get_student_profiles(site, graduated_year)

        # Get meta courses data and generate headers
        meta_courses, courses_headers, header_to_index = cls.get_meta_courses_data(student_profiles)

        # Prepare student data
        student_data, _ = cls.prepare_student_data(student_profiles, meta_courses, graduated_year)

        # Create CSV response
        return cls.create_csv_response(student_data, courses_headers, header_to_index, graduated_year)
