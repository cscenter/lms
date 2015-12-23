# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime

import six
import unicodecsv
from collections import OrderedDict, defaultdict

from django.core.urlresolvers import reverse
from django.views import generic
from django.http import HttpResponse, JsonResponse
from braces.views import LoginRequiredMixin, JSONResponseMixin

from core.views import SuperUserOnlyMixin
from learning.viewmixins import CuratorOnlyMixin
from learning.models import StudentProject
from learning.utils import get_current_semester_pair
from users.models import CSCUser, CSCUserFilter


class StudentSearchJSONView(CuratorOnlyMixin, JSONResponseMixin, generic.View):
    content_type = u"application/javascript; charset=utf-8"
    limit = 1000

    def get(self, request, *args, **kwargs):
        qs = CSCUser.objects.values('first_name', 'last_name', 'pk')
        filter = CSCUserFilter(request.GET, qs)
        # FIXME: move to CSCUserFilter
        if filter.empty_query:
            return JsonResponse(dict(users=[], there_is_more=False))
        filtered_users = filter.qs[:self.limit + 1]
        for u in filtered_users:
            u['url'] = reverse('user_detail', args=[u['pk']])
        # return HttpResponse("<html><body>body tag should be returned</body></html>", content_type='text/html; charset=utf-8')
        # TODO: JsonResponse returns unicode. Hard to debug.
        return self.render_json_response({
            "total": len(filtered_users[:self.limit]),
            "users": filtered_users[:self.limit],
            "there_is_more": len(filtered_users) > self.limit
        })


class StudentSearchView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/student_search.html"

    def get_context_data(self, **kwargs):
        context = super(StudentSearchView, self).get_context_data(**kwargs)
        context['json_api_uri'] = reverse('student_search_json')
        context['enrollment_years'] = (CSCUser.objects
                                       .values_list('enrollment_year', flat=True)
                                       .filter(enrollment_year__isnull=False)
                                       .order_by('enrollment_year')
                                       .distinct())
        context['groups'] = CSCUserFilter.FILTERING_GROUPS
        context['groups'] = {gid: CSCUser.group_pks[gid] for gid in
                             context["groups"]}
        context['status'] = CSCUser.STATUS
        context["status"] = {sid: name for sid, name in context["status"]}
        context["cnt_enrollments"] = range(CSCUserFilter.ENROLLMENTS_CNT_LIMIT + 1)
        return context

class StudentsDiplomasView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, **kwargs):
        context = super(StudentsDiplomasView, self).get_context_data(**kwargs)
        context['students'] = CSCUser.objects.students_info(only_will_graduate=True)
        for student in context['students']:
            student.projects = StudentProject.sorted(student.projects)

        return context


class StudentsDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info(only_will_graduate=True)

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
        for course_id, course_name in six.iteritems(courses_headers):
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        for i in xrange(1, shads_max + 1):
            headers.append('ШАД, курс {}, название'.format(i))
            headers.append('ШАД, курс {}, оценка'.format(i))
        for i in xrange(1, projects_max + 1):
            headers.append('Проект {}, оценка'.format(i))
            headers.append('Проект {}, руководитель(и)'.format(i))
            headers.append('Проект {}, семестр'.format(i))
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
                    row.extend([p.name, p.supervisor, p.semester])
                else:
                    row.extend(['', '', ''])
            w.writerow(row)

        return response


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"


class StudentsAllSheetCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info(only_will_graduate=False)

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
        shads_max = 0
        online_courses_max = 0
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

            if len(s.online_courses) > online_courses_max:
                online_courses_max = len(s.online_courses)

            if len(s.projects) > projects_max:
                projects_max = len(s.projects)
            s.projects = StudentProject.sorted(s.projects)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "sheet_{}.csv".format(datetime.datetime.now().year)
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)
        w = unicodecsv.writer(response, encoding='utf-8')

        headers = [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год выпуска',
            'Почта',
            'Яндекс ID',
            'Телефон',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Сдано курсов',
            'Ссылка на профиль',
        ]
        for course_id, course_name in six.iteritems(courses_headers):
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        for i in xrange(1, projects_max + 1):
            headers.append('Проект {}, оценка'.format(i))
            headers.append('Проект {}, руководитель(и)'.format(i))
            headers.append('Проект {}, семестр(ы)'.format(i))
        for i in xrange(1, shads_max + 1):
            headers.append('ШАД, курс {}, название'.format(i))
            headers.append('ШАД, курс {}, преподаватели'.format(i))
            headers.append('ШАД, курс {}, оценка'.format(i))
        for i in xrange(1, online_courses_max + 1):
            headers.append('Онлайн-курс {}, название'.format(i))
        w.writerow(headers)

        for s in students:
            row = [
                s.last_name,
                s.first_name,
                s.patronymic,
                "+" if s.is_volunteer else "",
                s.university,
                s.uni_year_at_enrollment,
                s.enrollment_year,
                s.graduation_year,
                s.email,
                s.yandex_id,
                s.phone,
                " и ".join((s.name for s in s.study_programs.all())),
                s.status_display,
                '',
                s.comment,
                s.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
                s.workplace,
                len(s.courses) + len(s.shads) + len(s.online_courses),
                request.build_absolute_uri(s.get_absolute_url())
            ]

            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            s.projects.extend([None] * (projects_max - len(s.projects)))
            for p in s.projects:
                if p is not None:
                    semesters = [unicode(sem) for sem in p.semesters.all()]
                    row.extend([p.name, p.supervisor, ", ".join(semesters)])
                else:
                    row.extend(['', '', ''])

            s.shads.extend([None] * (shads_max - len(s.shads)))
            for shad in s.shads:
                if shad is not None:
                    row.extend([shad.name, shad.teachers, shad.grade_display])
                else:
                    row.extend(['', '', ''])

            s.online_courses.extend([None] * (online_courses_max -
                                              len(s.online_courses)))
            for online_course in s.online_courses:
                if online_course is not None:
                    row.extend([online_course.name])
                else:
                    row.extend([''])

            w.writerow(row)
        return response


class StudentsSheetCurrentSemesterCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        students = CSCUser.objects.students_info(
            only_will_graduate=False,
            enrollments_current_semester_only=True)

        # Prepare courses and student projects data
        courses_headers = OrderedDict()
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

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        year, semester_type = get_current_semester_pair()
        filename = "sheet_{}_{}.csv".format(year, semester_type)
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)
        w = unicodecsv.writer(response, encoding='utf-8')

        headers = [
            'Фамилия',
            'Имя',
            'Отчество',
            'Вольнослушатель',
            'ВУЗ',
            'Курс (на момент поступления)',
            'Год поступления',
            'Год выпуска',
            'Почта',
            'Яндекс ID',
            'Телефон',
            'Направления обучения',
            'Статус',
            'Дата статуса или итога (изменения)',
            'Комментарий',
            'Дата последнего изменения комментария',
            'Работа',
            'Ссылка на профиль',
        ]
        for course_id, course_name in six.iteritems(courses_headers):
            headers.append(course_name + ', оценка')
            headers.append(course_name + ', преподаватели')
        w.writerow(headers)

        for s in students:
            row = [
                s.last_name,
                s.first_name,
                s.patronymic,
                "+" if s.is_volunteer else "",
                s.university,
                s.uni_year_at_enrollment,
                s.enrollment_year,
                s.graduation_year,
                s.email,
                s.yandex_id,
                s.phone,
                " и ".join((s.name for s in s.study_programs.all())),
                s.status_display,
                '',
                s.comment,
                s.comment_changed_at.strftime("%H:%M %d.%m.%Y"),
                s.workplace,
                request.build_absolute_uri(s.get_absolute_url())
            ]

            for course_id in courses_headers:
                sc = s.courses[course_id]
                row.extend([sc['grade'], sc['teachers']])

            w.writerow(row)

        return response
