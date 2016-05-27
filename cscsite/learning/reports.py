# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import six

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import OrderedDict, defaultdict
from learning.settings import GRADES, STUDENT_STATUS
from users.models import CSCUser


# TODO: Exclude some headers for target semester
class ProgressReport(object):
    # TODO: Maybe can use report.data even in diplomas view to simplify it
    """
    Process students info from CSCUser manager for future export in
    CSV of XLSX format.
    Example:
        students_info = CSCUser.objects.students_info()
        report = ProgressReportFull(students_info)
        print(report.headers)
        for raw_row in report.data:
            row = report.export_row(raw_row)
            print(row)
    """

    __metaclass__ = ABCMeta

    def __init__(self, honest_grade_system=False, target_semester=None,
                 request=None):
        courses_headers = OrderedDict()
        # Max count values among all students
        self.shads_max = 0
        self.online_courses_max = 0
        self.projects_max = 0
        self.target_semester = target_semester
        self.request = request
        students_data = self.get_queryset(term=self.target_semester)
        for s in students_data:
            self.before_process_row(s)

            student_courses = defaultdict(lambda: {'teachers': '', 'grade': ''})
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
                    "grade": grade.lower(),
                    "teachers": ", ".join(teachers)
                }
            s.courses = student_courses

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

    @abstractmethod
    def export_row(self, row):
        raise NotImplementedError()

    def _export_row_append_courses(self, row, student):
        for course_id in self.courses_headers:
            sc = student.courses[course_id]
            row.extend([sc['grade'], sc['teachers']])

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
            'Направления'
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
            " и ".join(s.name for s in student.study_programs.all())
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
        return CSCUser.objects.students_info()

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
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
            'Сдано курсов (Центр/Клуб/ШАД/Онлайн) всего',
        ]

    def generate_headers(self):
        headers = self.static_headers
        self._append_courses_headers(headers)
        self._append_projects_headers(headers)
        self._append_shad_courses_headers(headers)
        self._append_online_courses_headers(headers)
        return headers

    def export_row(self, student):
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            "+" if student.is_volunteer else "",
            student.email,
            student.phone,
            student.university,
            student.uni_year_at_enrollment,
            student.enrollment_year,
            student.graduation_year,
            student.yandex_id,
            " и ".join(s.name for s in student.study_programs.all()),
            student.status_display,
            '',  # FIXME: missed value??
            student.comment,
            student.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
            student.workplace,
            self.request.build_absolute_uri(student.get_absolute_url()),
            len(student.courses) + len(student.shads) + len(
                student.online_courses),
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
            include_not_graded=True
        )

    def before_process_row(self, student):
        student.enrollments_in_target_semester = 0
        student.success_eq_target_semester = 0
        student.success_lt_target_semester = 0
        # Note: Include shad courses even ungraded or `unsatisfactory`
        student.shads = [c for c in student.shads if
                         c.semester_id == self.target_semester.pk]
        # FIXME: include online and shads in stats for success_lt_target_semester!!!

    def skip_enrollment(self, enrollment, student):
        """
        Count stats for enrollments from passed terms and skip them.
        For target term skip `not graded` enrollments if target semester
        already passed.
        """
        # Note: Failed courses rejected on query level.
        assert enrollment.grade != GRADES.unsatisfactory
        if enrollment.course_offering.semester == self.target_semester:
            student.enrollments_in_target_semester += 1
            if enrollment.grade != GRADES.not_graded:
                student.success_eq_target_semester += 1
        else:
            if enrollment.grade != GRADES.not_graded:
                student.success_lt_target_semester += 1
            # Hide all passed enrollments in report
            return True
        return False

    @property
    def static_headers(self):
        return [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
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
            'Сдано курсов (Центр/Клуб/ШАД/Онлайн) всего до семестра "%s"' %
            self.target_semester,
            'Сдано курсов (Центр/Клуб/ШАД/Онлайн) за семестр "%s"' %
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
            row.append(sc['grade'])

    def export_row(self, student):
        row = [
            student.last_name,
            student.first_name,
            student.patronymic,
            "+" if student.is_volunteer else "",
            student.email,
            student.phone,
            student.university,
            student.uni_year_at_enrollment,
            student.enrollment_year,
            student.graduation_year,
            student.yandex_id,
            " и ".join(s.name for s in student.study_programs.all()),
            student.status_display,
            '', # FIXME: missed value?
            student.comment,
            student.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
            student.workplace,
            self.request.build_absolute_uri(student.get_absolute_url()),
            student.success_lt_target_semester,
            student.success_eq_target_semester,
            # Note: included all online courses until target semester
            student.enrollments_in_target_semester
        ]
        self._export_row_append_courses(row, student)
        self._export_row_append_shad_courses(row, student)
        self._export_row_append_online_courses(row, student)
        return row

    def get_filename(self):
        return "sheet_{}_{}".format(self.target_semester.year,
                                    self.target_semester.type)
