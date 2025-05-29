"""
Services for diploma export functionality.
"""
import csv
import datetime
from typing import Dict, List, Set, Tuple, Any, Iterable

from django.http import HttpResponse
from django.db.models import Q, Prefetch, Case, When, Value, IntegerField, QuerySet

from courses.models import MetaCourse
from learning.models import Enrollment
from learning.settings import GradeTypes, StudentStatuses
from users.constants import GenderTypes
from users.models import StudentProfile, SHADCourseRecord, StudentTypes


class ElectronicDiplomaExportService:
    """
    Service for exporting student data for electronic diplomas.
    """

    @staticmethod
    def get_courses_grades(enrollments):
        """
        Returns a dictionary mapping course indexes to grade displays for all courses
        where there is at least one grade.
        """
        result = {}

        for enrollment in enrollments:
            course_index = enrollment.course.meta_course.index
            if course_index:
                result[course_index] = enrollment.grade_display.lower()

        return result

    @staticmethod
    def get_student_profiles(site, graduated_year: int) -> QuerySet:
        """
        Get student profiles for electronic diplomas export with optimized prefetching.
        - Students and partner student with the status Will be graduated.
        - If the user has both a master's degree and just a student, we take just a student.
        - Students with the status Graduate, but the year of graduation from the university == graduated_year.
        - There will only be SHAD (reg) courses.
        - There will only be satisfactory_grades, except for Re-credit (no grade).
        """

        return StudentProfile.objects.filter(
                Q(status=StudentStatuses.WILL_GRADUATE) | Q(status=StudentStatuses.GRADUATE, graduation_year=graduated_year),
                site_id=site.id,
                type__in=[StudentTypes.REGULAR, StudentTypes.PARTNER],
            ).annotate(
                # Add a priority field - lower value means higher priority
                type_priority=Case(
                    When(type=StudentTypes.REGULAR, then=Value(1)),
                    When(type=StudentTypes.PARTNER, then=Value(2)),
                    output_field=IntegerField(),
                )
            ).order_by(
                'user', 'type_priority'  # Order by user first, then by priority (REGULAR first)
            ).distinct(
                'user'
            ).select_related(
                'user',
                'branch',
                'user__yandex_data'
            ).prefetch_related(
                Prefetch(
                    'user__enrollment_set',
                    queryset=Enrollment.objects.filter(
                        Q(grade__in=GradeTypes.satisfactory_grades) & Q(grade__ne=GradeTypes.RE_CREDIT),
                        is_deleted=False,
                        course__main_branch__site_id=site.id,
                        course__meta_course__index__isnull=False
                    ).select_related('course__meta_course'),
                    to_attr='prefetched_enrollments'
                ),
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
            header = f"{mc.index}:evaluation" if mc.index else f"{mc.name}:evaluation"
            courses_headers.append(header)
            header_to_index[header] = mc.index

        return meta_courses, courses_headers, header_to_index

    @classmethod
    def prepare_student_data(cls, student_profiles: Iterable[StudentProfile], meta_courses: Dict[str, str],
                            graduated_year: int) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """
        Prepare student data for CSV export.
        """
        courses_with_grades = set()
        student_data = []

        for profile in student_profiles:
            user = profile.user

            # Get courses with grades for this student
            course_results = cls.get_courses_grades(profile.user.prefetched_enrollments)
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
                len(course_results),
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
