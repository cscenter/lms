# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import six

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import OrderedDict, defaultdict

from core.views import ReportFileOutput
from learning.settings import GRADES, STUDENT_STATUS
from learning.utils import get_grade_index, is_positive_grade
from users.models import CSCUser


# TODO: filter projects by grade?
class ProgressReport(ReportFileOutput):
    """
    Process students info from CSCUser manager for future export in
    CSV of XLSX format. Stores separately headers and data.
    Example:
        report = ProgressReportFull()
        print(report.headers)
        for raw_row in report.data:
            row = report.export_row(raw_row)
            print(row)
    """

    __metaclass__ = ABCMeta

    def __init__(self, honest_grade_system=False, target_semester=None,
                 request=None):
        # Max count values among all students
        self.shads_max = 0
        self.online_courses_max = 0
        self.projects_max = 0
        self.target_semester = target_semester
        self.request = request
        students_data = self.get_queryset(term=self.target_semester)
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
                    e.course_offering.course_id] = e.course_offering.course.name
                teachers = [t.get_full_name() for t in
                            e.course_offering.teachers.all()]
                if honest_grade_system:
                    grade = e.grade_honest
                else:
                    grade = e.grade_display
                if e.course_offering.course_id in student_courses:
                    # Store the highest grade
                    # TODO: add tests
                    record = student_courses[e.course_offering.course_id]
                    new_grade_index = get_grade_index(e.grade)
                    if new_grade_index > get_grade_index(record["grade"]):
                        student_courses[e.course_offering.course_id] = {
                            "grade": e.grade,
                            "grade_str": grade.lower(),
                            "teachers": ", ".join(teachers),
                            "is_open": e.course_offering.is_open
                        }
                else:
                    student_courses[e.course_offering.course_id] = {
                        "grade": e.grade,
                        "grade_str": grade.lower(),
                        "teachers": ", ".join(teachers),
                        "is_open": e.course_offering.is_open
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
        for course_id, course_name in six.iteritems(self.courses_headers):
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
        return is_positive_grade(grade)

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

    def get_applicant_form_absolute_url(self, student):
        applicant_form_url = student.get_applicant_form_url()
        if applicant_form_url:
            return self.request.build_absolute_uri(applicant_form_url)
        else:
            return ""


class ProgressReportForDiplomas(ProgressReport):
    @staticmethod
    def get_queryset(**kwargs):
        """
        Explicitly exclude rows with bad grades (or without) on query level.
        """
        return CSCUser.objects.students_info(
            filters={
                "status": CSCUser.STATUS.will_graduate
            },
            exclude_grades=[GRADES.unsatisfactory, GRADES.not_graded]
        )

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
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
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.university,
            " и ".join(s.name for s in student.areas_of_study.all()),
            self.passed_courses_total(student),
            self.get_applicant_form_absolute_url(student),
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_projects(row, student)
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "diplomas_{}".format(today.year)

    def passed_courses_total(self, student):
        """Don't consider adjustment for club courses"""
        center = 0
        club = 0
        shad = 0
        online = len(student.online_courses)
        for c in student.courses.values():
            if is_positive_grade(c['grade']):
                if c['is_open']:
                    club += 1
                else:
                    center += 1
        for c in student.shads:
            shad += int(is_positive_grade(c.grade))
        return center + club + shad + online


class ProgressReportFull(ProgressReport):
    @staticmethod
    def get_queryset(**kwargs):
        return (CSCUser.objects
                .students_info()
                .select_related("applicant"))

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
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.city_id,
            "+" if student.is_volunteer else "",
            "+" if student.is_master_student else "",
            student.email,
            student.phone,
            student.university,
            student.get_uni_year_at_enrollment_display(),
            student.enrollment_year,
            student.curriculum_year,
            student.graduation_year,
            student.yandex_id,
            " и ".join(s.name for s in student.areas_of_study.all()),
            student.get_status_display(),
            '',  # FIXME: error in student.status_changed_at field
            student.comment,
            student.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
            student.workplace,
            self.request.build_absolute_uri(student.get_absolute_url()),
            self.get_applicant_form_absolute_url(student),
            total_success_passed,
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_projects(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_online_courses(row, student)
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "sheet_{}".format(today.strftime("%d.%m.%Y"))


class ProgressReportForSemester(ProgressReport):
    """
    Input data must contain all enrollments for student until target
    semester (inclusive), even without grade to collect stats.
    Exported data contains club and center courses if target term already
    passed and additionally shad- and online-courses if target term is current.
    """

    UNSUCCESSFUL_GRADES = [GRADES.not_graded, GRADES.unsatisfactory]

    @staticmethod
    def get_queryset(**kwargs):
        assert "term" in kwargs
        return CSCUser.objects.students_info(
            filters={
                "groups__in": [
                    CSCUser.group.STUDENT_CENTER,
                    CSCUser.group.VOLUNTEER
                ],
            },
            exclude={
                "status": STUDENT_STATUS.expelled
            },
            semester=kwargs["term"],
        )

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

    def skip_enrollment(self, enrollment, student):
        """
        Count stats for enrollments from passed terms and skip them.
        """
        if enrollment.course_offering.semester == self.target_semester:
            student.enrollments_eq_target_semester += 1
            if enrollment.grade not in self.UNSUCCESSFUL_GRADES:
                student.success_eq_target_semester += 1
        else:
            if enrollment.grade not in self.UNSUCCESSFUL_GRADES:
                student.success_lt_target_semester.add(
                    enrollment.course_offering.course_id
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
        for course_id, course_name in six.iteritems(self.courses_headers):
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
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.city_id,
            "+" if student.is_volunteer else "",
            "+" if student.is_master_student else "",
            student.email,
            student.phone,
            student.university,
            student.get_uni_year_at_enrollment_display(),
            student.enrollment_year,
            student.curriculum_year,
            student.graduation_year,
            student.yandex_id,
            " и ".join(s.name for s in student.areas_of_study.all()),
            student.get_status_display(),
            '',  # FIXME: error with student.status_changed_at
            student.comment,
            student.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
            student.workplace,
            self.request.build_absolute_uri(student.get_absolute_url()),
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
