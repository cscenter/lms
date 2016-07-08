# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import io

import six

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import OrderedDict, defaultdict

import unicodecsv
from django.http import HttpResponse
from django.utils.encoding import force_text
from xlsxwriter import Workbook

from learning.settings import GRADES, STUDENT_STATUS
from users.models import CSCUser


# TODO: filter projects by grade?
class ProgressReport(object):
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
            student_courses = defaultdict(lambda: {'teachers': '',
                                                   'grade': '',  # code
                                                   'grade_repr': ''})
            for e in s.enrollments:
                if self.skip_enrollment(e, s):
                    continue
                courses_headers[
                    e.course_offering.course.id] = e.course_offering.course.name
                teachers = [t.get_full_name() for t in
                            e.course_offering.teachers.all()]
                if honest_grade_system:
                    grade = e.grade_honest
                else:
                    grade = e.grade_display
                student_courses[e.course_offering.course.id] = {
                    "grade": e.grade,
                    "grade_repr": grade.lower(),
                    "teachers": ", ".join(teachers)
                }
            s.courses = student_courses

            self.after_process_row(s)

            if len(s.shads) > self.shads_max:
                self.shads_max = len(s.shads)

            if len(s.online_courses) > self.online_courses_max:
                self.online_courses_max = len(s.online_courses)

            if len(s.projects) > self.projects_max:
                self.projects_max = len(s.projects)
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

    @abstractproperty
    def static_headers(self):
        """Returns array of headers, that always included in report"""
        pass

    @abstractmethod
    def generate_headers(self):
        raise NotImplementedError("ProgressReport: undefined headers")

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
        # Shad course
        if hasattr(course, "grade"):
            grade = course.grade
        else:
            # Club or center course
            grade = course["grade"]
        return grade not in [GRADES.unsatisfactory, GRADES.not_graded, '']

    @abstractmethod
    def export_row(self, row):
        raise NotImplementedError()

    def _export_row_append_courses(self, row, student):
        for course_id in self.courses_headers:
            sc = student.courses[course_id]
            row.extend([sc['grade_repr'], sc['teachers']])

    def _export_row_append_projects(self, row, student):
        student.projects.extend(
            [None] * (self.projects_max - len(student.projects)))
        for p in student.projects:
            if p is not None:
                row.extend([p.name, p.get_grade_display(), p.supervisor,
                            p.semester])
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

    def output_csv(self):
        output = io.BytesIO()
        w = unicodecsv.writer(output, encoding='utf-8')

        w.writerow(self.headers)
        for student in self.data:
            row = self.export_row(student)
            w.writerow(row)

        output.seek(0)
        response = HttpResponse(output.read(),
                                content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = \
            'attachment; filename="{}.csv"'.format(self.get_filename())
        return response

    def output_xlsx(self):
        output = io.BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        format_bold = workbook.add_format({'bold': True})
        for index, header in enumerate(self.headers):
            worksheet.write(0, index, header, format_bold)

        for row_index, raw_row in enumerate(self.data, start=1):
            row = self.export_row(raw_row)
            for col_index, value in enumerate(row):
                value = "" if value is None else force_text(value)
                worksheet.write(row_index, col_index, force_text(value))

        workbook.close()
        output.seek(0)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response = HttpResponse(output.read(), content_type=content_type)
        response['Content-Disposition'] = \
            'attachment; filename="{}.xlsx"'.format(self.get_filename())
        return response

    def get_filename(self):
        today = datetime.datetime.now()
        return "report_".format(today.strftime("%d.%m.%Y"))


class ProgressReportForDiplomas(ProgressReport):
    @staticmethod
    def get_queryset(**kwargs):
        return CSCUser.objects.students_info(filters={
            "status": CSCUser.STATUS.will_graduate
        })

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Университет',
            'Направления',
            'Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего',
        ]

    def generate_headers(self):
        headers = self.static_headers
        self._append_courses_headers(headers)
        self._append_shad_courses_headers(headers)
        self._append_projects_headers(headers)
        return headers

    def export_row(self, student):
        total_success_passed = (len(student.courses) +
                                len(student.shads) +
                                len(student.online_courses))
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            student.university,
            " и ".join(s.name for s in student.study_programs.all()),
            total_success_passed
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_projects(row, student)
        return row

    def get_filename(self):
        today = datetime.datetime.now()
        return "diplomas_{}".format(today.year)


class ProgressReportFull(ProgressReport):
    @staticmethod
    def get_queryset(**kwargs):
        return CSCUser.objects.students_info(
            exclude_grades=[]
        )

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
            'Магистратура',
            'Почта',
            'Телефон',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год выпуска',
            'Яндекс ID',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Ссылка на профиль',
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
            "+" if student.is_volunteer else "",
            "+" if student.is_master else "",
            student.email,
            student.phone,
            student.university,
            student.uni_year_at_enrollment,
            student.enrollment_year,
            student.graduation_year,
            student.yandex_id,
            " и ".join(s.name for s in student.study_programs.all()),
            student.status_display,
            '',  # FIXME: error in student.status_changed_at field
            student.comment,
            student.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
            student.workplace,
            self.request.build_absolute_uri(student.get_absolute_url()),
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
    @staticmethod
    def get_queryset(**kwargs):
        assert "term" in kwargs
        return CSCUser.objects.students_info(
            filters={
                "groups__in": [
                    CSCUser.group_pks.STUDENT_CENTER,
                    CSCUser.group_pks.VOLUNTEER
                ],
            },
            exclude={
                "status": STUDENT_STATUS.expelled
            },
            semester=kwargs["term"],
            exclude_grades=[GRADES.unsatisfactory]
        )

    def before_process_row(self, student):
        student.enrollments_eq_target_semester = 0
        student.success_eq_target_semester = 0
        student.success_lt_target_semester = 0
        # Shad courses specific attributes
        student.success_shad_eq_target_semester = 0
        student.success_shad_lt_target_semester = 0

    def after_process_row(self, student):
        if not student.shads:
            return
        shads = []
        # Note: failed shad courses rejected on query level
        for shad in student.shads:
            if shad.semester == self.target_semester:
                if shad.grade != GRADES.not_graded:
                    student.success_shad_eq_target_semester += 1
                shads.append(shad)
            elif shad.grade != GRADES.not_graded:
                student.success_shad_lt_target_semester += 1
        student.shads = shads

    def skip_enrollment(self, enrollment, student):
        """
        Count stats for enrollments from passed terms and skip them.
        For target term skip `not graded` enrollments if target semester
        already passed.
        """
        # Note: Failed courses rejected on query level.
        assert enrollment.grade != GRADES.unsatisfactory
        if enrollment.course_offering.semester == self.target_semester:
            student.enrollments_eq_target_semester += 1
            if enrollment.grade != GRADES.not_graded:
                student.success_eq_target_semester += 1
        else:
            if enrollment.grade != GRADES.not_graded:
                student.success_lt_target_semester += 1
            # Hide enrollments from terms less than target semester
            return True
        return False

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
            'Магистратура',
            'Почта',
            'Телефон',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
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
            'Записей на курсы за семестр "%s"' % self.target_semester
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
            row.append(sc['grade_repr'])

    def export_row(self, student):
        success_total_lt_target_semester = (
            student.success_lt_target_semester +
            student.success_shad_lt_target_semester +
            len(student.online_courses))
        success_total_eq_target_semester = (
            student.success_eq_target_semester +
            student.success_shad_eq_target_semester)
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            "+" if student.is_volunteer else "",
            "+" if student.is_master else "",
            student.email,
            student.phone,
            student.university,
            student.uni_year_at_enrollment,
            student.enrollment_year,
            student.graduation_year,
            student.yandex_id,
            " и ".join(s.name for s in student.study_programs.all()),
            student.status_display,
            '',  # FIXME: error with student.status_changed_at
            student.comment,
            student.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
            student.workplace,
            self.request.build_absolute_uri(student.get_absolute_url()),
            success_total_lt_target_semester,
            success_total_eq_target_semester,
            student.enrollments_eq_target_semester
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_online_courses(row, student)
        return row

    def get_filename(self):
        return "sheet_{}_{}".format(self.target_semester.year,
                                    self.target_semester.type)
