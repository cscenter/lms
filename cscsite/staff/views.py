# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import unicodecsv

from collections import OrderedDict, defaultdict

from django.views import generic
from django.http import HttpResponse

from core.views import StaffOnlyMixin, SuperUserOnlyMixin
from learning.models import StudentProject
from users.models import CSCUser


class StudentsDiplomasView(SuperUserOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, **kwargs):
        context = super(StudentsDiplomasView, self).get_context_data(**kwargs)
        context['students'] = CSCUser.objects.students_info(only_graduate=True)
        for student in context['students']:
            student.projects = StudentProject.sorted(student.projects)

        return context


class StudentsDiplomasCSVView(SuperUserOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info(only_graduate=True)

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
        shads_max = 0
        projects_max = 0
        for s in students:
            student_courses = defaultdict(lambda: {'teachers': '', 'grade': ''})
            for e in s.enrollments:
                courses_headers[e.course_offering.course.id] = \
                    e.course_offering.course.name
                teachers = [t.get_full_name() for t
                            in e.course_offering.teachers.all()]
                student_courses[e.course_offering.course.id] = dict(
                    grade=e.grade_display.lower(),
                    teachers=", ".join(teachers)
                )
            s.courses = student_courses

            if len(s.shads) > shads_max:
                shads_max = len(s.shads)

            if len(s.projects) > projects_max:
                projects_max = len(s.projects)
            s.projects = StudentProject.sorted(s.projects)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "diplomas_{}.csv".format(datetime.datetime.now().year)
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)
        w = unicodecsv.writer(response, encoding='utf-8')

        headers = ['Фамилия', 'Имя', 'Отчество', 'Университет', 'Направления']
        for course_id, course_name in courses_headers.iteritems():
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        for i in xrange(1, shads_max + 1):
            headers.append('ШАД, курс {}, название'.format(i))
            headers.append('ШАД, курс {}, оценка'.format(i))
        for i in xrange(1, projects_max + 1):
            headers.append('Проект {}, оценка'.format(i))
            headers.append('Проект {}, руководитель(и)'.format(i))
            headers.append('Проект {}, семестр(ы)'.format(i))
        w.writerow(headers)

        for s in students:
            row = [s.last_name, s.first_name, s.patronymic, s.university,
                   " и ".join((s.name for s in s.study_programs.all()))]
            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            s.shads.extend([None] * (shads_max - len(s.shads)))
            for shad in s.shads:
                if shad is not None:
                    row.extend([shad.name, shad.grade])
                else:
                    row.extend(['', ''])

            s.projects.extend([None] * (projects_max - len(s.projects)))
            for p in s.projects:
                if p is not None:
                    semesters = [unicode(sem) for sem in p.semesters.all()]
                    row.extend([p.name, p.supervisor, ", ".join(semesters)])
                else:
                    row.extend(['', '', ''])
            w.writerow(row)

        return response


class ExportsView(StaffOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"


class StudentsAllSheetCSVView(StaffOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info(only_graduate=True)

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
        shads_max = 0
        projects_max = 0
        for s in students:
            student_courses = defaultdict(lambda: {'teachers': '', 'grade': ''})
            for e in s.enrollments:
                courses_headers[e.course_offering.course.id] = \
                    e.course_offering.course.name
                teachers = [t.get_full_name() for t
                            in e.course_offering.teachers.all()]
                student_courses[e.course_offering.course.id] = dict(
                    grade=e.grade_display.lower(),
                    teachers=", ".join(teachers)
                )
            s.courses = student_courses

            if len(s.shads) > shads_max:
                shads_max = len(s.shads)

            if len(s.projects) > projects_max:
                projects_max = len(s.projects)
            s.projects = StudentProject.sorted(s.projects)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "diplomas_{}.csv".format(datetime.datetime.now().year)
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)
        w = unicodecsv.writer(response, encoding='utf-8')

        headers = ['Фамилия', 'Имя', 'Отчество', 'Университет', 'Направления']
        for course_id, course_name in courses_headers.iteritems():
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        for i in xrange(1, shads_max + 1):
            headers.append('ШАД, курс {}, название'.format(i))
            headers.append('ШАД, курс {}, оценка'.format(i))
        for i in xrange(1, projects_max + 1):
            headers.append('Проект {}, оценка'.format(i))
            headers.append('Проект {}, руководитель(и)'.format(i))
            headers.append('Проект {}, семестр(ы)'.format(i))
        w.writerow(headers)

        for s in students:
            row = [s.last_name, s.first_name, s.patronymic, s.university,
                   " и ".join((s.name for s in s.study_programs.all()))]
            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            s.shads.extend([None] * (shads_max - len(s.shads)))
            for shad in s.shads:
                if shad is not None:
                    row.extend([shad.name, shad.grade])
                else:
                    row.extend(['', ''])

            s.projects.extend([None] * (projects_max - len(s.projects)))
            for p in s.projects:
                if p is not None:
                    semesters = [unicode(sem) for sem in p.semesters.all()]
                    row.extend([p.name, p.supervisor, ", ".join(semesters)])
                else:
                    row.extend(['', '', ''])
            w.writerow(row)

        return response
