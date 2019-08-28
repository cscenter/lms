# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from collections import OrderedDict, defaultdict
from datetime import datetime

from django.db.models import Q, Prefetch, Count
from django.utils import formats

from core.reports import ReportFileOutput
from learning.models import AssignmentComment, Enrollment
from courses.models import Semester
from learning.permissions import has_master_degree
from projects.models import ReportComment, ProjectStudent
from learning.settings import StudentStatuses, GradeTypes
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from learning.utils import grade_to_mark
from users.constants import Roles
from users.models import User, SHADCourseRecord


class ProgressReport(ReportFileOutput):
    """
    Process students info from User manager for future export in
    CSV of XLSX format. Stores separately headers and data.
    Example:
        report = ProgressReportFull()
        print(report.headers)
        for raw_row in report.data:
            row = report.export_row(raw_row)
            print(row)
    """

    __metaclass__ = ABCMeta

    def __init__(self, honest_grade_system=False, qs_filters=None):
        # Max count values among all students
        self.shads_max = 0
        self.online_courses_max = 0
        self.projects_max = 0
        qs_filters = qs_filters or {}
        students_data = self.get_queryset(**qs_filters)
        # Collect course headers and prepare enrollments info
        courses_headers = OrderedDict()
        for s in students_data:
            self.before_process_row(s)
            # FIXME: What if we have 2 course offerings for the course, where one is_open=True, but other is_open=False
            student_courses = defaultdict(lambda: {'teachers': '',
                                                   'grade': '',  # code
                                                   'grade_str': '',
                                                   'is_open': False})
            for e in s.enrollments:
                if self.skip_enrollment(e, s):
                    continue
                courses_headers[
                    e.course.meta_course_id] = e.course.meta_course.name
                teachers = [t.get_full_name() for t in e.course.teachers.all()]
                if honest_grade_system:
                    grade = e.grade_honest
                else:
                    grade = e.grade_display
                if e.course.meta_course_id in student_courses:
                    # Store the highest grade
                    # TODO: add tests
                    record = student_courses[e.course.meta_course_id]
                    new_grade_index = grade_to_mark(e.grade)
                    if new_grade_index > grade_to_mark(record["grade"]):
                        student_courses[e.course.meta_course_id] = {
                            "grade": e.grade,
                            "grade_str": grade.lower(),
                            "teachers": ", ".join(teachers),
                            "is_open": e.course.is_open
                        }
                else:
                    student_courses[e.course.meta_course_id] = {
                        "grade": e.grade,
                        "grade_str": grade.lower(),
                        "teachers": ", ".join(teachers),
                        "is_open": e.course.is_open
                    }
            s.courses = student_courses

            self.after_process_row(s)

            if len(s.shads) > self.shads_max:
                self.shads_max = len(s.shads)

            if len(s.online_courses) > self.online_courses_max:
                self.online_courses_max = len(s.online_courses)

            if len(s.projects_through) > self.projects_max:
                self.projects_max = len(s.projects_through)
        self.courses_headers = courses_headers
        self.headers = self.generate_headers()
        self.data = students_data

    def before_process_row(self, student):
        pass

    def after_process_row(self, student):
        """Add additional logic here if necessary"""
        pass

    def skip_enrollment(self, enrollment, student):
        """
        Returns True if enrollment should be skipped. Default implementation
        returns ``False``.
        """
        return False

    @staticmethod
    @abstractmethod
    def get_queryset(**kwargs):
        raise NotImplementedError("ProgressReport: undefined queryset")

    @property
    @abstractmethod
    def static_headers(self):
        """Returns array of headers, that always included in report"""
        pass

    @abstractmethod
    def generate_headers(self):
        return self.static_headers

    def _append_courses_headers(self, headers):
        for course_id, course_name in self.courses_headers.items():
            headers.extend([
                "{}, оценка".format(course_name),
                "{}, преподаватели".format(course_name)
            ])

    def _append_projects_headers(self, headers):
        for i in range(1, self.projects_max + 1):
            headers.extend([
                'Проект {}, название'.format(i),
                'Проект {}, оценка'.format(i),
                'Проект {}, руководитель(и)'.format(i),
                'Проект {}, семестр'.format(i)
            ])

    def _append_shad_courses_headers(self, headers):
        for i in range(1, self.shads_max + 1):
            headers.extend([
                'ШАД, курс {}, название'.format(i),
                'ШАД, курс {}, преподаватели'.format(i),
                'ШАД, курс {}, оценка'.format(i)
            ])

    def _append_online_courses_headers(self, headers):
        for i in range(1, self.online_courses_max + 1):
            headers.append('Онлайн-курс {}, название'.format(i))

    @staticmethod
    def is_positive_grade(course):
        """Check shad or club/center course is successfully passed"""
        # Skip dummy course
        if course is None:
            return False
        if hasattr(course, "grade"):  # SHAD course
            grade = course.grade
        else:  # Club or Center course
            grade = course["grade"]
        return grade in GradeTypes.satisfactory_grades

    def _export_row_append_courses(self, row, student):
        for course_id in self.courses_headers:
            c = student.courses[course_id]
            row.extend([c['grade_str'], c['teachers']])

    def _export_row_append_projects(self, row, student):
        student.projects_through.extend(
            [None] * (self.projects_max - len(student.projects_through)))
        for ps in student.projects_through:
            if ps is not None:
                row.extend([ps.project.name,
                            ps.get_final_grade_display(),
                            ps.project.supervisor,
                            ps.project.semester])
            else:
                row.extend(['', '', '', ''])

    def _export_row_append_shad_courses(self, row, student):
        student.shads.extend(
            [None] * (self.shads_max - len(student.shads)))
        for shad in student.shads:
            if shad is not None:
                row.extend([shad.name,
                            shad.teachers,
                            shad.grade_display.lower()])
            else:
                row.extend(['', '', ''])

    def _export_row_append_online_courses(self, row, student):
        student.online_courses.extend([None] * (
            self.online_courses_max - len(student.online_courses)))
        for online_course in student.online_courses:
            if online_course is not None:
                row.extend([online_course.name])
            else:
                row.extend([''])

    def get_applicant_forms(self, student):
        urls = []
        for a in student.applicant_set.all():
            urls.append(a.get_absolute_url())
        return "\r\n".join(urls)


class ProgressReportForDiplomas(ProgressReport):
    @staticmethod
    def get_queryset(**filters):
        """
        Explicitly exclude rows with bad grades (or without) on query level.
        """
        filters = {
            "status": StudentStatuses.WILL_GRADUATE,
            **filters
        }
        return (User.objects
                .has_role(Roles.STUDENT,
                          Roles.GRADUATE,
                          Roles.VOLUNTEER)
                .students_info(filters=filters,
                               exclude_grades=[GradeTypes.UNSATISFACTORY,
                                               GradeTypes.NOT_GRADED]))

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Почта',
            'Университет',
            'Направления',
            'Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего',
            'Ссылка на анкету',
        ]

    def generate_headers(self):
        headers = self.static_headers
        self._append_courses_headers(headers)
        self._append_shad_courses_headers(headers)
        self._append_projects_headers(headers)
        return headers

    def export_row(self, student):
        if hasattr(student, "graduate_profile"):
            disciplines = student.graduate_profile.academic_disciplines.all()
        else:
            disciplines = []
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.email,
            student.university,
            " и ".join(s.name for s in disciplines),
            self.passed_courses_total(student),
            self.get_applicant_forms(student),
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_projects(row, student)
        return row

    def get_filename(self):
        today = datetime.now()
        return "diplomas_{}".format(today.year)

    def passed_courses_total(self, student):
        """Don't consider adjustment for club courses"""
        center = 0
        club = 0
        shad = 0
        online = len(student.online_courses)
        for c in student.courses.values():
            if c['grade'] in GradeTypes.satisfactory_grades:
                if c['is_open']:
                    club += 1
                else:
                    center += 1
        for c in student.shads:
            shad += int(c.grade in GradeTypes.satisfactory_grades)
        return center + club + shad + online


class ProgressReportFull(ProgressReport):
    @staticmethod
    def get_queryset(**kwargs):
        return (User.objects
                .has_role(Roles.STUDENT,
                          Roles.GRADUATE,
                          Roles.VOLUNTEER)
                .students_info()
                .prefetch_related("applicant_set"))

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Город',
            'Вольнослушатель',
            'Магистратура',
            'Почта',
            'Телефон',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год программы обучения',
            'Год выпуска',
            'Яндекс ID',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Ссылка на профиль',
            'Ссылка на анкету',
            'Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего',
        ]

    def generate_headers(self):
        headers = self.static_headers
        self._append_courses_headers(headers)
        self._append_projects_headers(headers)
        self._append_shad_courses_headers(headers)
        self._append_online_courses_headers(headers)
        return headers

    def export_row(self, student):
        total_success_passed = (
            sum(1 for c in student.courses.values() if
                self.is_positive_grade(c)) +
            sum(1 for c in student.shads if self.is_positive_grade(c)) +
            sum(1 for _ in student.online_courses)
        )
        dt_format = f"{TIME_FORMAT_RU} {DATE_FORMAT_RU}"
        if hasattr(student, "graduate_profile"):
            disciplines = student.graduate_profile.academic_disciplines.all()
        else:
            disciplines = []
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.city_id,
            "+" if student.is_volunteer else "",
            "+" if has_master_degree(student) else "",
            student.email,
            student.phone,
            student.university,
            student.get_uni_year_at_enrollment_display(),
            student.enrollment_year,
            student.curriculum_year,
            student.graduation_year,
            student.yandex_login,
            " и ".join(s.name for s in disciplines),
            student.get_status_display(),
            '',  # FIXME: error in student.status_changed_at field
            student.comment,
            student.comment_changed_at.strftime(dt_format),
            student.workplace,
            student.get_absolute_url(),
            self.get_applicant_forms(student),
            total_success_passed,
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_projects(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_online_courses(row, student)
        return row

    def get_filename(self):
        today = formats.date_format(datetime.now(), "SHORT_DATE_FORMAT")
        return f"sheet_{today}"


class ProgressReportForSemester(ProgressReport):
    """
    Input data must contain all enrollments for student until target
    semester (inclusive), even without grade to collect stats.
    Exported data contains club and center courses if target term already
    passed and additionally shad- and online-courses if target term is current.
    """

    UNSUCCESSFUL_GRADES = [GradeTypes.NOT_GRADED, GradeTypes.UNSATISFACTORY]

    def __init__(self, term, honest_grade_system=False, qs_filters=None):
        self.target_semester = term
        qs_filters = qs_filters or {}
        qs_filters["semester"] = self.target_semester
        super().__init__(honest_grade_system, qs_filters)

    @staticmethod
    def get_queryset(**kwargs):
        semester = kwargs.pop("semester")
        filters = kwargs.pop("filters", {})
        return (User.objects
                .has_role(Roles.STUDENT, Roles.VOLUNTEER)
                .students_info(filters=filters,
                               exclude={"status": StudentStatuses.EXPELLED},
                               semester=semester))

    def before_process_row(self, student):
        student.enrollments_eq_target_semester = 0
        # During one term student can't enroll on 1 course twice, but for
        # previous terms we should consider this situation and count only
        # unique course ids
        student.success_eq_target_semester = 0
        student.success_lt_target_semester = set()
        # Shad courses specific attributes
        student.shad_eq_target_semester = 0
        student.success_shad_eq_target_semester = 0
        student.success_shad_lt_target_semester = 0

    def after_process_row(self, student):
        """
        Convert `success_lt_target_semester` to int repr.
        Collect statistics for shad courses.
        """
        student.success_lt_target_semester = len(
            student.success_lt_target_semester)
        if not student.shads:
            return
        shads = []
        # During one term student can't enroll on 1 course twice, for
        # previous terms we assume they can't do that.
        for shad in student.shads:
            if shad.semester == self.target_semester:
                student.shad_eq_target_semester += 1
                if shad.grade not in self.UNSUCCESSFUL_GRADES:
                    student.success_shad_eq_target_semester += 1
                # Show shad enrollments for target term only
                shads.append(shad)
            elif shad.grade not in self.UNSUCCESSFUL_GRADES:
                student.success_shad_lt_target_semester += 1
        student.shads = shads

    def skip_enrollment(self, enrollment: Enrollment, student):
        """
        Count stats for enrollments from passed terms and skip them.
        """
        if enrollment.course.semester == self.target_semester:
            student.enrollments_eq_target_semester += 1
            if enrollment.grade not in self.UNSUCCESSFUL_GRADES:
                student.success_eq_target_semester += 1
        else:
            if enrollment.grade not in self.UNSUCCESSFUL_GRADES:
                student.success_lt_target_semester.add(
                    enrollment.course.meta_course_id
                )
            # Show enrollments for target term only
            return True
        return False

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Город',
            'Вольнослушатель',
            'Магистратура',
            'Почта',
            'Телефон',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год программы обучения',
            'Год выпуска',
            'Яндекс ID',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Ссылка на профиль',
            'Успешно сдано (Центр/Клуб/ШАД/Онлайн) всего до семестра "%s"' %
            self.target_semester,
            'Успешно сдано (Центр/Клуб/ШАД) за семестр "%s"' %
            self.target_semester,
            'Записей на курсы (Центр/Клуб/ШАД) за семестр "%s"' %
            self.target_semester
        ]

    def _append_courses_headers(self, headers):
        for course_id, course_name in self.courses_headers.items():
            headers.append("{}, оценка".format(course_name))

    def generate_headers(self):
        headers = self.static_headers
        self._append_courses_headers(headers)
        self._append_shad_courses_headers(headers)
        self._append_online_courses_headers(headers)
        return headers

    def _export_row_append_courses(self, row, student):
        for course_id in self.courses_headers:
            sc = student.courses[course_id]
            row.append(sc['grade_str'])

    def export_row(self, student):
        success_total_lt_target_semester = (
            student.success_lt_target_semester +
            student.success_shad_lt_target_semester +
            len(student.online_courses))
        success_total_eq_target_semester = (
            student.success_eq_target_semester +
            student.success_shad_eq_target_semester)
        enrollments_eq_target_semester = (
            student.enrollments_eq_target_semester +
            student.shad_eq_target_semester
        )
        dt_format = f"{TIME_FORMAT_RU} {DATE_FORMAT_RU}"
        if hasattr(student, "graduate_profile"):
            disciplines = student.graduate_profile.academic_disciplines.all()
        else:
            disciplines = []
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.city_id,
            "+" if student.is_volunteer else "",
            "+" if has_master_degree(student) else "",
            student.email,
            student.phone,
            student.university,
            student.get_uni_year_at_enrollment_display(),
            student.enrollment_year,
            student.curriculum_year,
            student.graduation_year,
            student.yandex_login,
            " и ".join(s.name for s in disciplines),
            student.get_status_display(),
            '',  # FIXME: error with student.status_changed_at
            student.comment,
            student.comment_changed_at.strftime(dt_format),
            student.workplace,
            student.get_absolute_url(),
            success_total_lt_target_semester,
            success_total_eq_target_semester,
            enrollments_eq_target_semester
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_online_courses(row, student)
        return row

    def get_filename(self):
        return "sheet_{}_{}".format(self.target_semester.year,
                                    self.target_semester.type)


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
                AssignmentComment.objects
                .filter(student_assignment__student_id=student.pk)
                .filter(time_range_in_utc)
                .count())
            report_comments_after_23 = (
                ReportComment.objects
                .filter(author_id=student.pk)
                .filter(time_range_in_utc)
                .count())
            comments_after_23_total = report_comments_after_23 + assignment_comments_after_23
            # 2. Сколько вообще комментариев на сайте центра
            assignment_comments_count = (
                AssignmentComment.objects
                .filter(student_assignment__student_id=student.pk)
                .count())
            report_comments_count = (
                ReportComment.objects
                .filter(author_id=student.pk)
                .count())
            comments_total = assignment_comments_count + report_comments_count
            # 3. (курсы с оценкой зачёт и выше) / (все взятые курсы)
            enrollments_qs = student.enrollment_set.filter(is_deleted=False)
            all_enrollments_count = (enrollments_qs.count() +
                                     student.onlinecourserecord_set.count() +
                                     student.shadcourserecord_set.count())
            passed = (stats["passed"]["total"]) / all_enrollments_count
            # 4. Максимальное количество сданных курсов + практик за один
            # семестр, какой именно это семестр
            # Collect all unique terms among practices, center, shad and
            # club courses
            all_enrollments_terms = enrollments_qs.values_list(
                "course__semester_id",
                flat=True)
            semesters = {v for v in all_enrollments_terms}
            all_shad_terms = (SHADCourseRecord.objects
                              .filter(student_id=student.pk)
                              .values_list("semester_id", flat=True))
            unique_shad_terms = {v for v in all_shad_terms}
            all_projects_terms = (ProjectStudent.objects
                                  .filter(student_id=student.pk)
                                  .values_list("project__semester_id",
                                               flat=True))
            project_semesters = {v for v in all_projects_terms}
            semesters = semesters.union(unique_shad_terms, project_semesters)
            max_in_term = 0
            max_in_term_semester_id = 0
            for semester_id in semesters:
                enrollments_in_term_qs = enrollments_qs.filter(
                    course__semester_id=semester_id).all()
                in_term = sum(int(e.grade in GradeTypes.satisfactory_grades) for e in
                              enrollments_in_term_qs)
                projects_in_term_qs = ProjectStudent.objects.filter(
                    project__semester_id=semester_id,
                    student_id=student.pk).all()
                in_term += sum(int(p.final_grade in GradeTypes.satisfactory_grades) for p in
                               projects_in_term_qs)
                shad_courses_in_term_qs = SHADCourseRecord.objects.filter(
                    student_id=student.pk, semester_id=semester_id).all()
                in_term += sum(int(c.grade in GradeTypes.satisfactory_grades) for c in
                               shad_courses_in_term_qs)
                if in_term > max_in_term:
                    max_in_term = in_term
                    max_in_term_semester_id = semester_id
            # 6. Сколько проектов сдано осенью?
            projects_qs = ProjectStudent.objects.filter(
                project__semester__type="autumn", student_id=student.pk).all()
            projects_in_autumn = sum(
                int(p.final_grade in GradeTypes.satisfactory_grades) for p in projects_qs)
            # 7. Сколько проектов сдано весной?
            projects_qs = ProjectStudent.objects.filter(
                project__semester__type="spring", student_id=student.pk).all()
            projects_in_spring = sum(
                int(p.final_grade in GradeTypes.satisfactory_grades) for p in projects_qs)
            row = [
                student.city.name,
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
            Enrollment.active
            .select_related(
                'course',
                'course__semester',
                'course__meta_course',)
            .annotate(classes_total=Count('course__courseclass'))
            .order_by('student', 'course_id'))
        shad_courses_queryset = (SHADCourseRecord.objects
                                 .select_related("semester"))
        prefetch_list = [
            Prefetch('enrollment_set', queryset=enrollments_queryset),
            Prefetch('shadcourserecord_set', queryset=shad_courses_queryset),
            'onlinecourserecord_set',
        ]
        qs = (User.objects
              .filter(status=StudentStatuses.WILL_GRADUATE)
              .prefetch_related(*prefetch_list))
        return qs

    def export_row(self, row):
        return row

    def get_filename(self):
        today = datetime.now()
        return "will_graduate_report_{}".format(
            formats.date_format(today, "SHORT_DATE_FORMAT"))