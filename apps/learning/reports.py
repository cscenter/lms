import io
from abc import ABCMeta, abstractmethod
from operator import attrgetter
from typing import Dict, List, Literal, Set

from pandas import DataFrame, ExcelWriter

from django.conf import settings
from django.db.models import Case, Count, F, IntegerField, Prefetch, Q, When
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, FileResponse

from admission.models import Applicant
from core.reports import ReportFileOutput
from courses.constants import SemesterTypes
from courses.models import Course, MetaCourse, Semester, CourseDurations
from courses.selectors import course_teachers_prefetch_queryset
from courses.utils import get_term_index
from learning.models import AssignmentComment, Enrollment, GraduateProfile
from learning.settings import GradeTypes, StudentStatuses
from learning.utils import grade_to_mark
from projects.constants import ProjectGradeTypes, ProjectTypes
from projects.models import Project, ProjectStudent, ReportComment
from users.managers import (
    get_enrollments_progress,
    get_projects_progress,
    get_shad_courses_progress,
)
from users.models import SHADCourseRecord, StudentProfile, StudentTypes, User


def dataframe_to_response(df: DataFrame, output_format: str, filename: str):
    if output_format == "csv":
        return DataFrameResponse.as_csv(df, filename)
    elif output_format == "xlsx":
        return DataFrameResponse.as_xlsx(df, filename)
    raise ValueError("Supported output formats: csv, xlsx")


class DataFrameResponse:
    @staticmethod
    def as_csv(df: DataFrame, filename):
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, mode="wb")
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"{filename}.csv")

    @staticmethod
    def as_xlsx(df: DataFrame, filename):
        output = io.BytesIO()
        writer = ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, index=False)
        writer.save()
        output.seek(0)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response = HttpResponse(output.read(), content_type=content_type)
        response["Content-Disposition"] = 'attachment; filename="{}.xlsx"'.format(
            filename
        )
        return response


def generate_projects_headers(headers_number):
    return [
        h
        for i in range(1, headers_number + 1)
        for h in (
            f"Проект {i}, название",
            f"Проект {i}, оценка",
            f"Проект {i}, руководители",
            f"Проект {i}, семестр",
        )
    ]


def generate_shad_courses_headers(headers_number):
    return [
        h
        for i in range(1, headers_number + 1)
        for h in (
            f"ШАД, курс {i}, название",
            f"ШАД, курс {i}, преподаватели",
            f"ШАД, курс {i}, оценка",
        )
    ]


def generate_online_courses_headers(headers_number):
    return [f"Онлайн-курс {i}, название" for i in range(1, headers_number + 1)]


def is_club_course_map(courses):
    meta_course_is_club: Dict[int, bool] = {}
    for course in courses.values():
        key = course.meta_course_id
        if key in meta_course_is_club:
            # XXX: keep in mind that a metacourse could be a CSC course and a
            # CS Club course in different terms.
            # Note: In CSV for 2020 graduates only "Functional programming"
            # was held both in CSC and CS Club at some point,
            # currently considered as a CSC course
            if meta_course_is_club[key] != course.is_club_course:
                meta_course_is_club[key] = False
        else:
            meta_course_is_club[key] = course.is_club_course
    return meta_course_is_club

def duration_course_map(courses):
    meta_course_duration: Dict[int, bool] = {}
    for course in courses.values():
        meta_course_duration[course.meta_course_id] = course.duration
    return meta_course_duration

class ProgressReport:
    """
    Generates report for students progress: courses, shad/online courses
    and projects.

    Usage example:
        # Call `.grade_honest` method on `Enrollment` model
        report = ProgressReport(grade_getter="grade_honest")
        custom_queryset = report.get_queryset().filter(pk=404)
        df: pandas.DataFrame = report.generate(custom_queryset)
        # Return response in csv format
        response = DataFrameResponse.as_csv(df, 'report_file.csv')
    """

    __metaclass__ = ABCMeta

    def __init__(
        self,
        grade_getter="grade_display",
        on_course_duplicate: Literal["store_last", "store_max"] = "store_last",
    ):
        """
        Two options to choose what grade to export when student take
        a course multiple times:
            *store_last* - grade from the last satisfactory passed course
            *store_max* - the highest grade
        """
        self.grade_getter = attrgetter(grade_getter)
        self.on_course_duplicate = on_course_duplicate

    @abstractmethod
    def get_queryset(self):
        return StudentProfile.objects.none()

    @abstractmethod
    def _generate_headers(
        self, *, courses, meta_courses, shads_max, online_max, projects_max
    ):
        return []

    @abstractmethod
    def _export_row(
        self,
        student_profile,
        *,
        courses,
        meta_courses,
        shads_max,
        online_max,
        projects_max,
    ):
        return []

    def get_courses_queryset(self, students):
        courses: Set[int] = set()
        for student in students:
            for e in student.enrollments_progress:
                courses.add(e.course_id)
        course_teachers = Prefetch(
            "course_teachers", queryset=course_teachers_prefetch_queryset()
        )
        qs = (
            Course.objects.filter(pk__in=courses)
            .select_related("meta_course", "main_branch", "semester")
            .only(
                "semester_id",
                "semester__index",
                "meta_course_id",
                "meta_course__name",
                "meta_course__slug",
                "grading_type",
                "main_branch_id",
                "main_branch__site_id",
            )
            .prefetch_related(course_teachers)
        )
        return qs

    def generate(self, queryset=None) -> DataFrame:
        student_profiles = queryset or self.get_queryset()
        # It's possible to prefetch all related courses but nested
        # .prefetch_related() for course teachers is extremely slow
        students = (sp.user for sp in student_profiles)
        unique_courses: Dict[int, Course] = {
            c.pk: c for c in self.get_courses_queryset(students)
        }
        unique_meta_courses: Dict[int, MetaCourse] = {}
        # Aggregate max number of courses for each type. Result headers
        # depend on these values.
        shads_max, online_max, projects_max = 0, 0, 0
        for student_profile in student_profiles:
            student_account = student_profile.user
            self.process_student(student_account, unique_courses, unique_meta_courses)
            shads_max = max(shads_max, len(student_account.shads))
            online_max = max(online_max, len(student_account.online_courses))
            projects_max = max(projects_max, len(student_account.projects_progress))

        # Alphabetically sort meta courses by name
        meta_course_names = [(mc.name, mc.pk) for mc in unique_meta_courses.values()]
        meta_course_names.sort()
        meta_courses: Dict[int, MetaCourse] = {}
        for _, pk in meta_course_names:
            meta_courses[pk] = unique_meta_courses[pk]

        headers = self._generate_headers(
            courses=unique_courses,
            meta_courses=meta_courses,
            shads_max=shads_max,
            online_max=online_max,
            projects_max=projects_max,
        )

        data = []
        for student_profile in student_profiles:
            row = self._export_row(
                student_profile,
                courses=unique_courses,
                meta_courses=meta_courses,
                shads_max=shads_max,
                online_max=online_max,
                projects_max=projects_max,
            )
            data.append(row)
        return DataFrame.from_records(columns=headers, data=data, index="ID")

    def process_student(self, student, unique_courses, unique_meta_courses):
        grades: Dict[int, Enrollment] = {}
        for enrollment in student.enrollments_progress:
            self.before_skip_enrollment(enrollment, student, unique_courses)
            if self.skip_enrollment(enrollment, student, unique_courses):
                continue
            course = unique_courses[enrollment.course_id]
            meta_course_id = course.meta_course_id
            unique_meta_courses[meta_course_id] = course.meta_course
            if meta_course_id in grades:
                current_enrollment = grades[meta_course_id]
                # Store the latest satisfactory grade
                if self.on_course_duplicate == "store_last":
                    current_course = unique_courses[current_enrollment.course_id]
                    is_current_grade_satisfactory = (
                        current_enrollment.grade in GradeTypes.satisfactory_grades
                    )
                    is_grade_satisfactory = (
                        enrollment.grade in GradeTypes.satisfactory_grades
                    )
                    is_grade_newer = (
                        course.semester.index > current_course.semester.index
                    )
                    if is_grade_satisfactory and (
                        is_grade_newer or not is_current_grade_satisfactory
                    ):
                        grades[meta_course_id] = enrollment
                # Stores the highest grade
                elif self.on_course_duplicate == "store_max":
                    # The behavior is not specified if different grading systems were
                    # used in different terms (e.g. 10-point scale and binary)
                    if grade_to_mark(enrollment.grade) > grade_to_mark(
                        current_enrollment.grade
                    ):
                        grades[meta_course_id] = enrollment
            else:
                grades[meta_course_id] = enrollment
        student.unique_enrollments = grades

    def before_skip_enrollment(self, enrollment, student, courses) -> None:
        """
        Hook for collecting stats. Called before .skip_enrollment method.
        """
        pass

    def skip_enrollment(self, enrollment, student, courses):
        return False

    def _export_courses(self, student, courses, meta_courses) -> List[str]:
        step = 2  # Number of columns for each course
        values = [""] * len(meta_courses) * step
        for i, meta_course_id in enumerate(meta_courses):
            if meta_course_id in student.unique_enrollments:
                enrollment = student.unique_enrollments[meta_course_id]
                course = courses[enrollment.course_id]
                teachers = ", ".join(
                    ct.teacher.get_abbreviated_name()
                    for ct in course.course_teachers.all()
                )
                values[i * step] = self.grade_getter(enrollment).lower()
                values[i * step + 1] = teachers
        return values

    def _export_projects(self, student, projects_max) -> List[str]:
        step = 4  # Number of columns for each project
        values = [""] * projects_max * step
        for i, ps in enumerate(student.projects_progress):
            values[i * step] = ps.project.name
            values[i * step + 1] = ps.get_final_grade_display()
            values[i * step + 2] = ", ".join(
                s.get_abbreviated_name() for s in ps.project.supervisors.all()
            )
            values[i * step + 3] = ps.project.semester
        return values

    def _export_shad_courses(self, student, shads_max) -> List[str]:
        step = 3  # Number of columns for each shad course
        values = [""] * shads_max * step
        for i, course in enumerate(student.shads):
            values[i * step] = course.name
            values[i * step + 1] = course.teachers
            values[i * step + 2] = course.grade_display.lower()
        return values

    def _export_online_courses(self, student, online_max) -> List[str]:
        values = [""] * online_max
        for i, course in enumerate(student.online_courses):
            values[i] = course.name
        return values

    @staticmethod
    def links_to_application_forms(student):
        return "\r\n".join(a.get_absolute_url() for a in student.applicant_set.all())


class FutureGraduateDiplomasReport(ProgressReport):
    def __init__(self, branch, **kwargs):
        super().__init__(**kwargs)
        self.branch = branch

    def get_queryset(self):
        exclude_grades = GradeTypes.unsatisfactory_grades
        enrollments_prefetch = get_enrollments_progress(
            lookup="user__enrollment_set", filters=[~Q(grade__in=exclude_grades)]
        )
        shad_courses_prefetch = get_shad_courses_progress(
            lookup="user__shadcourserecord_set", filters=[~Q(grade__in=exclude_grades)]
        )
        # Include all info about projects in CSV. Note: only successful projects are shown in the diplomas
        projects_prefetch = get_projects_progress(lookup="user__projectstudent_set")
        online_courses_prefetch = Prefetch(
            "user__onlinecourserecord_set", to_attr="online_courses"
        )
        return (
            StudentProfile.objects.filter(
                status=StudentStatuses.WILL_GRADUATE, branch=self.branch
            )
            .select_related("user")
            .prefetch_related(
                "academic_disciplines",
                "user__applicant_set",
                projects_prefetch,
                enrollments_prefetch,
                shad_courses_prefetch,
                online_courses_prefetch,
            )
            .order_by("user__last_name", "user__first_name", "user_id")
        )

    def _generate_headers(
        self, *, courses, meta_courses, shads_max, online_max, projects_max
    ):
        course_headers = []
        if meta_courses:
            meta_course_is_club = is_club_course_map(courses)

            def cs_club_prefix(meta_course_id):
                return "CS клуб: " if meta_course_is_club[meta_course_id] else ""

            course_headers = (
                h
                for meta_course_id, c in meta_courses.items()
                for h in (
                    f"{cs_club_prefix(meta_course_id)}{c.name}, оценка",
                    f"{cs_club_prefix(meta_course_id)}{c.name}, преподаватели",
                    f"{cs_club_prefix(meta_course_id)}{c.name}, семестр",
                )
            )

        shad_headers = (
            h
            for i in range(1, shads_max + 1)
            for h in (
                f"ШАД, курс {i}, название",
                f"ШАД, курс {i}, преподаватели",
                f"ШАД, курс {i}, оценка",
                f"ШАД, курс {i}, семестр",
            )
        )
        return [
            "ID",
            "Фамилия",
            "Имя",
            "Отчество",
            "Почта",
            "Университет",
            "Официальный студент",
            "Дата рождения",
            "Номер диплома ВУЗа",
            "Когда выдан",
            "Кем выдан",
            "Направления выпуска",
            "Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего",
            "Анкеты",
            *course_headers,
            *shad_headers,
            *generate_projects_headers(projects_max),
        ]

    def _export_row(
        self,
        student_profile,
        *,
        courses,
        meta_courses,
        shads_max,
        online_max,
        projects_max,
    ):
        disciplines = student_profile.academic_disciplines.all()
        student = student_profile.user
        return [
            student.pk,
            student.last_name,
            student.first_name,
            student.patronymic,
            student.email,
            student_profile.university,
            "да" if student_profile.is_official_student else "нет",
            student.birth_date,
            student_profile.diploma_number,
            student_profile.diploma_issued_on,
            student_profile.diploma_issued_by,
            " и ".join(s.name for s in disciplines),
            self.passed_courses_total(student, courses),
            self.links_to_application_forms(student),
            *self._export_courses(student, courses, meta_courses),
            *self._export_shad_courses(student, shads_max),
            *self._export_projects(student, projects_max),
        ]

    def _export_courses(self, student, courses, meta_courses) -> List[str]:
        step = 3  # Number of columns for each course
        values = [""] * len(meta_courses) * step
        for i, meta_course_id in enumerate(meta_courses):
            if meta_course_id in student.unique_enrollments:
                enrollment = student.unique_enrollments[meta_course_id]
                course = courses[enrollment.course_id]
                teachers = ", ".join(
                    ct.teacher.get_abbreviated_name()
                    for ct in course.course_teachers.all()
                )
                values[i * step] = self.grade_getter(enrollment).lower()
                values[i * step + 1] = teachers
                values[i * step + 2] = course.semester
        return values

    def _export_shad_courses(self, student, shads_max) -> List[str]:
        step = 4  # Number of columns for each shad course
        values = [""] * shads_max * step
        for i, course in enumerate(student.shads):
            values[i * step] = course.name
            values[i * step + 1] = course.teachers
            values[i * step + 2] = course.grade_display.lower()
            values[i * step + 3] = course.semester
        return values

    @staticmethod
    def passed_courses_total(student, courses):
        center = 0
        club = 0
        shad = 0
        online = len(student.online_courses)
        for enrollment in student.unique_enrollments.values():
            if enrollment.grade in GradeTypes.satisfactory_grades:
                course = courses[enrollment.course_id]
                if course.is_club_course:
                    club += 1
                else:
                    center += 1
        for course in student.shads:
            shad += int(course.grade in GradeTypes.satisfactory_grades)
        return center + club + shad + online


class OfficialDiplomasReport(ProgressReport):
    def __init__(self, diploma_issued_on, **kwargs):
        super().__init__(**kwargs)
        self.diploma_issued_on = diploma_issued_on

    def generate(self, queryset=None) -> DataFrame:
        student_profiles = queryset or self.get_queryset()
        # It's possible to prefetch all related courses but nested
        # .prefetch_related() is extremely slow, that's why we use map instead
        students = (sp.user for sp in student_profiles)
        unique_courses: Dict[int, Course] = {}
        for c in self.get_courses_queryset(students):
            unique_courses[c.pk] = c

        unique_meta_courses: Dict[int, MetaCourse] = {}
        unique_shad_courses: Set[str] = set()
        # Aggregate max number of courses for each type. Result headers
        # depend on these values.
        shads_max, online_max, projects_max = 0, 0, 0
        for student_profile in student_profiles:
            student = student_profile.user
            self.process_student(student, unique_courses, unique_meta_courses)
            self.process_shad(student, unique_shad_courses)
            shads_max = max(shads_max, len(student.shads))
            online_max = max(online_max, len(student.online_courses))
            projects_max = max(projects_max, len(student.projects_progress))

        headers = self._generate_headers(
            courses=unique_courses,
            meta_courses=unique_meta_courses,
            shad_courses=unique_shad_courses,
            shads_max=shads_max,
            online_max=online_max,
            projects_max=projects_max,
        )
        data = []
        for student_profile in student_profiles:
            row = self._export_row(
                student_profile,
                courses=unique_courses,
                meta_courses=unique_meta_courses,
                shad_courses=unique_shad_courses,
                shads_max=shads_max,
                online_max=online_max,
                projects_max=projects_max,
            )
            data.append(row)
        return DataFrame.from_records(columns=headers, data=data, index="ID")

    def get_queryset(self):
        exclude_grades = GradeTypes.unsatisfactory_grades
        exclude_project_grades = [
            ProjectGradeTypes.UNSATISFACTORY,
            ProjectGradeTypes.NOT_GRADED,
        ]
        enrollments_prefetch = get_enrollments_progress(
            lookup="user__enrollment_set", filters=[~Q(grade__in=exclude_grades)]
        )
        shad_courses_prefetch = get_shad_courses_progress(
            lookup="user__shadcourserecord_set", filters=[~Q(grade__in=exclude_grades)]
        )
        # Include all info about projects in CSV. Note: only successful projects are shown in the diplomas
        projects_prefetch = get_projects_progress(
            lookup="user__projectstudent_set",
            filters=[~Q(final_grade__in=exclude_project_grades)],
        )
        online_courses_prefetch = Prefetch(
            "user__onlinecourserecord_set", to_attr="online_courses"
        )
        return (
            StudentProfile.objects.select_related("user", "graduate_profile")
            .filter(graduate_profile__diploma_issued_on=self.diploma_issued_on)
            .prefetch_related(
                "academic_disciplines",
                "user__applicant_set",
                projects_prefetch,
                enrollments_prefetch,
                shad_courses_prefetch,
                online_courses_prefetch,
            )
            .order_by("user__last_name", "user__first_name", "user_id")
        )

    def _generate_headers(
        self,
        *,
        courses,
        meta_courses,
        shad_courses,
        shads_max,
        online_max,
        projects_max,
    ):
        course_headers = (c.name for c in meta_courses.values())
        shad_headers = (f"{c} (ШАД)" for c in shad_courses)
        project_headers = (f"Проект {i}" for i in range(1, projects_max + 1))
        return [
            "ID",
            "Фамилия",
            "Имя",
            "Отчество",
            "Регистрационный номер в АНО ДПО",
            "Номер диплома АНО ДПО",
            "Дата выдачи",
            "Дата рождения",
            "Номер диплома ВУЗа",
            "Когда выдан",
            "Кем выдан",
            *course_headers,
            *shad_headers,
            *project_headers,
        ]

    def _export_row(
        self,
        student_profile,
        *,
        courses,
        meta_courses,
        shad_courses,
        shads_max,
        online_max,
        projects_max,
    ):
        student = student_profile.user
        graduate_profile = student_profile.graduate_profile
        return [
            student.pk,
            student.last_name,
            student.first_name,
            student.patronymic,
            graduate_profile.diploma_registration_number,
            graduate_profile.diploma_number,
            graduate_profile.diploma_issued_on,
            student.birth_date,
            student_profile.diploma_number,
            student_profile.diploma_issued_on,
            student_profile.diploma_issued_by,
            *self._export_courses(student, courses, meta_courses),
            *self._export_shad_courses(student, shad_courses),
            *self._export_projects(student, projects_max),
        ]

    def _export_courses(self, student, courses, meta_courses) -> List[str]:
        values = [""] * len(meta_courses)
        for i, meta_course_id in enumerate(meta_courses):
            if meta_course_id in student.unique_enrollments:
                enrollment = student.unique_enrollments[meta_course_id]
                values[i] = self.grade_getter(enrollment).lower()
        return values

    def _export_projects(self, student, projects_max) -> List[str]:
        values = [""] * projects_max
        for i, ps in enumerate(student.projects_progress):
            values[i] = f"{ps.project.name}, {ps.get_final_grade_display().lower()}"
        return values

    def _export_shad_courses(self, student, shad_courses) -> List[str]:
        values = [""] * len(shad_courses)
        student_shad_courses = {c.name: c for c in student.shads}
        for i, shad_course in enumerate(shad_courses):
            if shad_course in student_shad_courses:
                course = student_shad_courses[shad_course]
                values[i] = course.grade_display.lower()
        return values

    def skip_enrollment(self, enrollment, student, courses):
        """Skip club courses"""
        course = courses[enrollment.course_id]
        return course.is_club_course

    def process_shad(self, student, unique_shad_courses):
        student_shad_courses = set(c.name for c in student.shads)
        unique_shad_courses |= student_shad_courses


class ProgressReportFull(ProgressReport):
    def get_queryset(self, base_queryset=None):
        enrollments_prefetch = get_enrollments_progress(
            lookup="user__enrollment_set",
        )
        shad_courses_prefetch = get_shad_courses_progress(
            lookup="user__shadcourserecord_set",
        )
        online_courses_prefetch = Prefetch(
            "user__onlinecourserecord_set", to_attr="online_courses"
        )
        projects_prefetch = get_projects_progress(lookup="user__projectstudent_set")

        if base_queryset is None:
            base_queryset = (
                StudentProfile.objects.filter(
                    type__in=[StudentTypes.REGULAR, StudentTypes.VOLUNTEER],
                    branch__site_id=settings.SITE_ID,
                )
                .select_related("user", "branch", "graduate_profile")
                .order_by("user__last_name", "user__first_name", "user__pk")
            )
        success_practice = Count(
            Case(
                When(
                    Q(
                        user__projectstudent__final_grade__in=ProjectGradeTypes.satisfactory_grades
                    )
                    & Q(
                        user__projectstudent__project__project_type=ProjectTypes.practice
                    )
                    & ~Q(
                        user__projectstudent__project__status=Project.Statuses.CANCELED
                    ),
                    then=F("user__projectstudent__id"),
                ),
                output_field=IntegerField(),
            ),
            distinct=True,
        )
        success_research = Count(
            Case(
                When(
                    Q(
                        user__projectstudent__final_grade__in=ProjectGradeTypes.satisfactory_grades
                    )
                    & Q(
                        user__projectstudent__project__project_type=ProjectTypes.research
                    )
                    & ~Q(
                        user__projectstudent__project__status=Project.Statuses.CANCELED
                    ),
                    then=F("user__projectstudent__id"),
                ),
                output_field=IntegerField(),
            ),
            distinct=True,
        )
        # Take into account only 1 enrollment if student passed the course twice
        success_enrollments_total = Count(
            Case(
                When(
                    Q(user__enrollment__grade__in=GradeTypes.satisfactory_grades)
                    & Q(user__enrollment__is_deleted=False),
                    then=F("user__enrollment__course__meta_course_id"),
                ),
                output_field=IntegerField(),
            ),
            distinct=True,
        )
        success_shad = Count(
            Case(
                When(
                    user__shadcourserecord__grade__in=GradeTypes.satisfactory_grades,
                    then=F("user__shadcourserecord__id"),
                ),
                output_field=IntegerField(),
            ),
            distinct=True,
        )
        success_online = Count("user__onlinecourserecord", distinct=True)
        return (
            base_queryset.defer(
                "graduate_profile__testimonial",
                "user__private_contacts",
                "user__social_networks",
                "user__bio",
            )
            .annotate(
                success_enrollments=success_enrollments_total,
                success_shad=success_shad,
                success_online=success_online,
                success_practice=success_practice,
                success_research=success_research,
            )
            .annotate(
                total_success_passed=(
                    F("success_enrollments") + F("success_shad") + F("success_online")
                )
            )
            .prefetch_related(
                Prefetch(
                    "user__applicant_set",
                    queryset=Applicant.objects.only("pk", "user_id"),
                ),
                "academic_disciplines",
                enrollments_prefetch,
                shad_courses_prefetch,
                online_courses_prefetch,
                projects_prefetch,
                "graduate_profile__academic_disciplines",
            )
        )

    def _generate_headers(
        self, *, courses, meta_courses, shads_max, online_max, projects_max, **kwargs
    ):
        course_headers = []
        if meta_courses:
            meta_course_is_club = is_club_course_map(courses)
            meta_course_duration = duration_course_map(courses)

            def cs_club_prefix(meta_course_id):
                return "[CS клуб] " if meta_course_is_club[meta_course_id] else ""

            def durability_prefix(meta_course_id):
                return "[Полусеместровый] " if meta_course_duration[meta_course_id] != CourseDurations.FULL else ""

            course_headers = (
                f"{durability_prefix(course.id)}{cs_club_prefix(course.id)}{course.name}"
                for course in meta_courses.values()
            )

        return [
            "ID",
            "Отделение",
            "Фамилия",
            "Имя",
            "Отчество",
            "Тип",
            _("User url"),
            "Пол",
            "Дата рождения",
            "Почта",
            "Telegram",
            "Телефон",
            "Номер пропуска",
            "Работа",
            "Яндекс ID",
            "Stepik ID",
            "Github Login",
            "ВУЗ",
            "Курс (на момент поступления)",
            "Год поступления",
            "Год программы обучения",
            "Год выпуска",
            "Официальный студент",
            "Номер диплома о высшем образовании",
            "Направления обучения",
            "Статус",
            "Комментарий",
            "Дата последнего изменения комментария",
            "Анкеты",
            "Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего",
            "Пройдено семестров практики(закончили, успех)",
            "Пройдено семестров НИР (закончили, успех)",
            *course_headers,
            *generate_shad_courses_headers(shads_max),
            *generate_online_courses_headers(online_max),
        ]

    def _export_row(
        self,
        student_profile,
        *,
        courses,
        meta_courses,
        shads_max,
        online_max,
        projects_max,
        **kwargs,
    ):
        try:
            disciplines = student_profile.graduate_profile.academic_disciplines.all()
            graduation_year = student_profile.graduate_profile.graduation_year
        except GraduateProfile.DoesNotExist:
            disciplines = student_profile.academic_disciplines.all()
            graduation_year = ""

        student_account = student_profile.user
        return [
            student_account.pk,
            student_profile.branch.name,
            student_account.last_name,
            student_account.first_name,
            student_account.patronymic,
            student_profile.get_type_display(),
            student_account.get_absolute_url(),
            student_account.get_gender_display(),
            student_account.birth_date,
            student_account.email,
            student_account.telegram_username,
            student_account.phone,
            student_account.badge_number,
            student_account.workplace,
            student_account.yandex_login,
            student_account.stepic_id if student_account.stepic_id else "",
            student_account.github_login if student_account.github_login else "",
            student_profile.university,
            student_profile.get_level_of_education_on_admission_display(),
            student_profile.year_of_admission,
            student_profile.year_of_curriculum
            if student_profile.year_of_curriculum
            else "",
            graduation_year,
            "да" if student_profile.is_official_student else "нет",
            student_profile.diploma_number if student_profile.diploma_number else "",
            " и ".join(s.name for s in disciplines),
            student_profile.get_status_display(),
            student_profile.comment,
            student_profile.get_comment_changed_at_display(),
            self.links_to_application_forms(student_account),
            student_profile.total_success_passed,
            student_profile.success_practice,
            student_profile.success_research,
            *self._export_courses(student_account, courses, meta_courses),
            *self._export_shad_courses(student_account, shads_max),
            *self._export_online_courses(student_account, online_max),
        ]

    def _export_courses(self, student, courses, meta_courses) -> List[str]:
        values = [""] * len(meta_courses)
        for i, meta_course_id in enumerate(meta_courses):
            if meta_course_id in student.unique_enrollments:
                enrollment = student.unique_enrollments[meta_course_id]
                values[i] = self.grade_getter(enrollment).lower()
        return values


class ProgressReportForSemester(ProgressReport):
    """
    Input data must contain all student enrollments until target
    semester (inclusive), even without grades.
    Exported data contains club and center courses if target term already
    passed and additionally shad- and online-courses if target term is current.
    """

    def __init__(self, term):
        self.target_semester = term
        super().__init__(grade_getter="grade_honest")

    def get_courses_queryset(self, students_queryset):
        return (
            super()
            .get_courses_queryset(students_queryset)
            .filter(semester__index__lte=self.target_semester.index)
        )

    def get_queryset_filters(self):
        return [
            Q(type__in=[StudentTypes.REGULAR, StudentTypes.VOLUNTEER]),
            Q(branch__site_id=settings.SITE_ID),
        ]

    def get_queryset(self):
        enrollments_prefetch = get_enrollments_progress(
            lookup="user__enrollment_set",
            filters=[Q(course__semester__index__lte=self.target_semester.index)],
        )
        shad_courses_prefetch = get_shad_courses_progress(
            lookup="user__shadcourserecord_set",
            filters=[Q(semester__index__lte=self.target_semester.index)],
        )
        projects_prefetch = get_projects_progress(lookup="user__projectstudent_set")
        online_courses_prefetch = Prefetch(
            "user__onlinecourserecord_set", to_attr="online_courses"
        )
        return (
            StudentProfile.objects.filter(*self.get_queryset_filters())
            .exclude(status__in=StudentStatuses.inactive_statuses)
            .select_related("user", "branch")
            .prefetch_related(
                "academic_disciplines",
                projects_prefetch,
                enrollments_prefetch,
                shad_courses_prefetch,
                online_courses_prefetch,
            )
            .order_by("user__last_name", "user__first_name", "user__pk")
        )

    def process_student(self, student, unique_courses, unique_meta_courses):
        student.enrollments_eq_target_semester = 0
        # During one term student can't enroll on 1 course twice, but for
        # previous terms we should consider this situation and count only
        # unique course ids
        student.success_eq_target_semester = 0
        student.success_lt_target_semester = set()
        # Process enrollments
        super().process_student(student, unique_courses, unique_meta_courses)
        student.success_lt_target_semester = len(student.success_lt_target_semester)
        # Shad courses stats
        student.shad_eq_target_semester = 0
        student.success_shad_eq_target_semester = 0
        student.success_shad_lt_target_semester = 0
        if student.shads:
            shads = []
            # During one term student can't enroll on 1 course twice, for
            # previous terms we assume they can't do that.
            for shad in student.shads:
                if shad.semester_id == self.target_semester.pk:
                    student.shad_eq_target_semester += 1
                    if shad.grade in GradeTypes.satisfactory_grades:
                        student.success_shad_eq_target_semester += 1
                    # Show shad enrollments for target term only
                    shads.append(shad)
                elif shad.grade in GradeTypes.satisfactory_grades:
                    student.success_shad_lt_target_semester += 1
            student.shads = shads
        # Projects stats
        projects_eq_target_semester = []
        success_inner_projects_lt_target_semester = 0
        success_external_projects_lt_target_semester = 0
        for ps in student.projects_progress:
            if ps.project.semester_id == self.target_semester.pk:
                projects_eq_target_semester.append(ps.project.get_absolute_url())
            elif ps.final_grade in ProjectGradeTypes.satisfactory_grades:
                is_ext = ps.project.is_external
                success_inner_projects_lt_target_semester += int(not is_ext)
                success_external_projects_lt_target_semester += int(is_ext)
        student.projects_eq_target_semester = projects_eq_target_semester
        student.success_inner_projects_lt_target_semester = (
            success_inner_projects_lt_target_semester
        )
        student.success_external_projects_lt_target_semester = (
            success_external_projects_lt_target_semester
        )

    def before_skip_enrollment(self, enrollment: Enrollment, student, courses):
        """Count stats for enrollments from the passed terms."""
        course = courses[enrollment.course_id]
        if course.semester_id == self.target_semester.pk:
            student.enrollments_eq_target_semester += 1
            if enrollment.grade in GradeTypes.satisfactory_grades:
                student.success_eq_target_semester += 1
        else:
            if enrollment.grade in GradeTypes.satisfactory_grades:
                student.success_lt_target_semester.add(course.meta_course_id)

    def skip_enrollment(self, enrollment: Enrollment, student, courses):
        """Show enrollments for the target term only."""
        course = courses[enrollment.course_id]
        return course.semester_id != self.target_semester.pk

    def _generate_headers(
        self, *, courses, meta_courses, shads_max, online_max, projects_max
    ):
        course_headers = (f"{course.name}, оценка" for course in meta_courses.values())
        return [
            "ID",
            "Отделение",
            "Фамилия",
            "Имя",
            "Отчество",
            _("User url"),
            "Почта",
            "Телефон",
            "Работа",
            "Яндекс ID",
            "Stepik ID",
            "Github Login",
            "ВУЗ",
            "Курс (на момент поступления)",
            "Год поступления",
            "Год программы обучения",
            "Номер семестра обучения",
            "Официальный студент",
            "Номер диплома о высшем образовании",
            "Направления обучения",
            "Статус",
            "Комментарий",
            "Дата последнего изменения комментария",
            'Успешно сдано (Центр/Клуб/ШАД/Онлайн) до семестра "%s"'
            % self.target_semester,
            'Успешно сдано (Центр/Клуб/ШАД) за семестр "%s"' % self.target_semester,
            'Записей на курсы (Центр/Клуб/ШАД) за семестр "%s"' % self.target_semester,
            'Успешных семестров внутренней практики/НИР до семестра "%s"'
            % self.target_semester,
            'Успешных семестров внешней практики/НИР до семестра "%s"'
            % self.target_semester,
            'Проекты за семестр "%s"' % self.target_semester,
            *course_headers,
            *generate_shad_courses_headers(shads_max),
            *generate_online_courses_headers(online_max),
        ]

    def _export_row(
        self,
        student_profile,
        *,
        courses,
        meta_courses,
        shads_max,
        online_max,
        projects_max,
    ):
        student = student_profile.user
        success_total_lt_target_semester = (
            student.success_lt_target_semester
            + student.success_shad_lt_target_semester
            + len(student.online_courses)
        )
        success_total_eq_target_semester = (
            student.success_eq_target_semester + student.success_shad_eq_target_semester
        )
        enrollments_eq_target_semester = (
            student.enrollments_eq_target_semester + student.shad_eq_target_semester
        )
        if student_profile.year_of_curriculum:
            curriculum_term_index = get_term_index(
                student_profile.year_of_curriculum, SemesterTypes.AUTUMN
            )
            term_order = self.target_semester.index - curriculum_term_index + 1
        else:
            term_order = "-"

        return [
            student.pk,
            student_profile.branch.name,
            student.last_name,
            student.first_name,
            student.patronymic,
            student.get_absolute_url(),
            student.email,
            student.phone,
            student.workplace,
            student.yandex_login,
            student.stepic_id if student.stepic_id else "",
            student.github_login if student.github_login else "",
            student_profile.university,
            student_profile.get_level_of_education_on_admission_display(),
            student_profile.year_of_admission,
            student_profile.year_of_curriculum
            if student_profile.year_of_curriculum
            else "",
            term_order,
            "да" if student_profile.is_official_student else "нет",
            student_profile.diploma_number if student_profile.diploma_number else "",
            " и ".join(s.name for s in student_profile.academic_disciplines.all()),
            student_profile.get_status_display(),
            student_profile.comment,
            student_profile.get_comment_changed_at_display(),
            success_total_lt_target_semester,
            success_total_eq_target_semester,
            enrollments_eq_target_semester,
            student.success_inner_projects_lt_target_semester,
            student.success_external_projects_lt_target_semester,
            "\r\n".join(student.projects_eq_target_semester),
            *self._export_courses(student, courses, meta_courses),
            *self._export_shad_courses(student, shads_max),
            *self._export_online_courses(student, online_max),
        ]

    def _export_courses(self, student, courses, meta_courses) -> List[str]:
        values = [""] * len(meta_courses)
        for i, meta_course_id in enumerate(meta_courses):
            if meta_course_id in student.unique_enrollments:
                enrollment = student.unique_enrollments[meta_course_id]
                values[i] = self.grade_getter(enrollment).lower()
        return values


class ProgressReportForInvitation(ProgressReportForSemester):
    def __init__(self, invitation):
        self.invitation = invitation
        term = invitation.semester
        super().__init__(term)

    def get_queryset_filters(self):
        student_profiles = Enrollment.objects.filter(invitation=self.invitation).values(
            "student_profile_id"
        )
        return [Q(type=StudentTypes.INVITED), Q(pk__in=student_profiles)]


class WillGraduateStatsReport(ReportFileOutput):
    """Unoptimized piece of code"""

    def __init__(self):
        self.headers = [
            "Город",
            "ФИО",
            "1. У кого сколько оставлено комментариев на сайте с 23:00 до 8:00 по мск (задания + проекты, входит отправка заданий)",
            "2. У кого сколько вообще комментариев на сайте центра (задания + проекты, входит отправка заданий)",
            "3. Процентное соотношение (курсы с оценкой зачёт и выше) / (все взятые курсы)",
            "4.1 Максимальное количество сданных курсов + практик за один семестр",
            "4.2 Какой именно это семестр",
            "5. Сколько проектов сдано осенью? ",
            "6. Сколько проектов сдано весной?",
            "7. Сдано курсов всего (ШАД/Клуб/Центр/Онлайн)",
            "8. Не сдал курсов всего (ШАД/Клуб/Центр/Онлайн)",
        ]

        self.data = []
        students = self.get_queryset()
        current_semester = Semester.get_current()
        for student in students.all():
            stats = student.stats(current_semester)
            # 1. Оставлено комментариев на сайте с 23:00 до 8:00 по мск
            time_range_in_utc = Q(created__hour__gte=20) | Q(created__hour__lte=5)
            assignment_comments_after_23 = (
                AssignmentComment.published.filter(
                    student_assignment__student_id=student.pk
                )
                .filter(time_range_in_utc)
                .count()
            )
            report_comments_after_23 = (
                ReportComment.objects.filter(author_id=student.pk)
                .filter(time_range_in_utc)
                .count()
            )
            comments_after_23_total = (
                report_comments_after_23 + assignment_comments_after_23
            )
            # 2. Сколько вообще комментариев на сайте центра
            assignment_comments_count = AssignmentComment.published.filter(
                student_assignment__student_id=student.pk
            ).count()
            report_comments_count = ReportComment.objects.filter(
                author_id=student.pk
            ).count()
            comments_total = assignment_comments_count + report_comments_count
            # 3. (курсы с оценкой зачёт и выше) / (все взятые курсы)
            enrollments_qs = student.enrollment_set.filter(is_deleted=False)
            all_enrollments_count = (
                enrollments_qs.count()
                + student.onlinecourserecord_set.count()
                + student.shadcourserecord_set.count()
            )
            passed = (stats["passed"]["total"]) / all_enrollments_count
            # 4. Максимальное количество сданных курсов + практик за один
            # семестр, какой именно это семестр
            # Collect all unique terms among practices, center, shad and
            # club courses
            all_enrollments_terms = enrollments_qs.values_list(
                "course__semester_id", flat=True
            )
            semesters = {v for v in all_enrollments_terms}
            all_shad_terms = SHADCourseRecord.objects.filter(
                student_id=student.pk
            ).values_list("semester_id", flat=True)
            unique_shad_terms = {v for v in all_shad_terms}
            all_projects_terms = ProjectStudent.objects.filter(
                student_id=student.pk
            ).values_list("project__semester_id", flat=True)
            project_semesters = {v for v in all_projects_terms}
            semesters = semesters.union(unique_shad_terms, project_semesters)
            max_in_term = 0
            max_in_term_semester_id = 0
            for semester_id in semesters:
                enrollments_in_term_qs = enrollments_qs.filter(
                    course__semester_id=semester_id
                ).all()
                in_term = sum(
                    int(e.grade in GradeTypes.satisfactory_grades)
                    for e in enrollments_in_term_qs
                )
                projects_in_term_qs = ProjectStudent.objects.filter(
                    project__semester_id=semester_id, student_id=student.pk
                ).all()
                in_term += sum(
                    int(p.final_grade in ProjectGradeTypes.satisfactory_grades)
                    for p in projects_in_term_qs
                )
                shad_courses_in_term_qs = SHADCourseRecord.objects.filter(
                    student_id=student.pk, semester_id=semester_id
                ).all()
                in_term += sum(
                    int(c.grade in GradeTypes.satisfactory_grades)
                    for c in shad_courses_in_term_qs
                )
                if in_term > max_in_term:
                    max_in_term = in_term
                    max_in_term_semester_id = semester_id
            # 6. Сколько проектов сдано осенью?
            projects_qs = ProjectStudent.objects.filter(
                project__semester__type="autumn", student_id=student.pk
            ).all()
            projects_in_autumn = sum(
                int(p.final_grade in ProjectGradeTypes.satisfactory_grades)
                for p in projects_qs
            )
            # 7. Сколько проектов сдано весной?
            projects_qs = ProjectStudent.objects.filter(
                project__semester__type="spring", student_id=student.pk
            ).all()
            projects_in_spring = sum(
                int(p.final_grade in ProjectGradeTypes.satisfactory_grades)
                for p in projects_qs
            )
            row = [
                student.branch.name,
                student.get_abbreviated_short_name(),
                comments_after_23_total,
                comments_total,
                "%.2f" % (passed * 100),
                max_in_term,
                Semester.objects.get(pk=max_in_term_semester_id),
                projects_in_autumn,
                projects_in_spring,
                stats["passed"]["total"],
                stats["failed"]["total"],
            ]
            self.data.append(row)

    def get_queryset(self):
        enrollments_queryset = (
            Enrollment.active.select_related(
                "course",
                "course__semester",
                "course__meta_course",
            )
            .annotate(classes_total=Count("course__courseclass"))
            .order_by("student", "course_id")
        )
        shad_courses_queryset = SHADCourseRecord.objects.select_related("semester")
        prefetch_list = [
            Prefetch("enrollment_set", queryset=enrollments_queryset),
            Prefetch("shadcourserecord_set", queryset=shad_courses_queryset),
            "onlinecourserecord_set",
        ]
        qs = (
            User.objects.filter(status=StudentStatuses.WILL_GRADUATE)
            .select_related("branch")
            .prefetch_related(*prefetch_list)
        )
        return qs

    def export_row(self, row):
        return row
