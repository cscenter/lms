# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import io
from collections import OrderedDict, defaultdict

import unicodecsv
from braces.views import JSONResponseMixin
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from django.views import generic
from xlsxwriter import Workbook

from learning.models import Semester
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester
from learning.settings import STUDENT_STATUS, FOUNDATION_YEAR, SEMESTER_TYPES
from learning.utils import get_current_semester_pair, get_term_index, get_term_by_index
from learning.viewmixins import CuratorOnlyMixin
from users.models import CSCUser, CSCUserFilter, CSCUserStatusLog


class StudentSearchJSONView(CuratorOnlyMixin, JSONResponseMixin, generic.View):
    content_type = u"application/javascript; charset=utf-8"
    limit = 500

    def get(self, request, *args, **kwargs):
        qs = CSCUser.objects.values('first_name', 'last_name', 'pk')
        filter = CSCUserFilter(request.GET, qs)
        # FIXME: move to CSCUserFilter
        if filter.empty_query:
            return JsonResponse(dict(users=[], there_is_more=False))
        filtered_users = filter.qs[:self.limit + 1]
        for u in filtered_users:
            u['url'] = reverse('user_detail', args=[u['pk']])
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
                                       .values_list('enrollment_year',
                                                    flat=True)
                                       .filter(enrollment_year__isnull=False)
                                       .order_by('enrollment_year')
                                       .distinct())
        context['groups'] = CSCUserFilter.FILTERING_GROUPS
        context['groups'] = {gid: CSCUser.group_pks[gid] for gid in
                             context["groups"]}
        context['status'] = CSCUser.STATUS
        context["status"] = {sid: name for sid, name in context["status"]}
        context["cnt_enrollments"] = range(
            CSCUserFilter.ENROLLMENTS_CNT_LIMIT + 1)
        return context


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    def get_context_data(self, **kwargs):
        context = super(ExportsView, self).get_context_data(**kwargs)
        year, term = get_current_semester_pair()
        current_term_index = get_term_index(year, term)
        context["current_term"] = {"year": year, "type": term}
        prev_term_year, prev_term = get_term_by_index(current_term_index - 1)
        context["prev_term"] = {"year": prev_term_year, "type": prev_term}
        return context
    template_name = "staff/exports.html"


class StudentsDiplomasView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, **kwargs):
        context = super(StudentsDiplomasView, self).get_context_data(**kwargs)
        context['students'] = ProgressReportForDiplomas.get_queryset()
        return context


class StudentsDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        progress_report = ProgressReportForDiplomas()

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(
            progress_report.get_filename())

        w = unicodecsv.writer(response, encoding='utf-8')
        w.writerow(progress_report.headers)
        for student in progress_report.data:
            row = progress_report.export_row(student)
            w.writerow(row)

        return response


class ProgressReportFullCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        progress_report = ProgressReportFull(honest_grade_system=True,
                                             request=request)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(
            progress_report.get_filename())
        w = unicodecsv.writer(response, encoding='utf-8')
        w.writerow(progress_report.headers)
        for student in progress_report.data:
            row = progress_report.export_row(student)
            w.writerow(row)
        return response


class ProgressReportForSemesterMixin(object):
    def get(self, request, *args, **kwargs):
        # Validate GET params
        try:
            term_year = int(self.kwargs['term_year'])
            if term_year < FOUNDATION_YEAR:
                raise ValueError("ProgressReportBySemester: Wrong year format")
            term_type = self.kwargs['term_type']
            if term_type not in SEMESTER_TYPES:
                raise ValueError("ProgressReportBySemester: Wrong term format")
            filters = {"year": term_year, "type": term_type}
            semester = get_object_or_404(Semester, **filters)
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        progress_report = ProgressReportForSemester(honest_grade_system=True,
                                                    target_semester=semester,
                                                    request=request)
        return self.generate_response(progress_report)

    def generate_response(self, progress_report):
        raise NotImplemented("ProgressReportBySemesterMixin: not implemented")


class ProgressReportForSemesterCSVView(CuratorOnlyMixin,
                                       ProgressReportForSemesterMixin,
                                       generic.base.View):
    http_method_names = ['get']

    def generate_response(self, progress_report):
        output = io.BytesIO()
        w = unicodecsv.writer(output, encoding='utf-8')

        w.writerow(progress_report.headers)
        for student in progress_report.data:
            row = progress_report.export_row(student)
            w.writerow(row)

        output.seek(0)
        response = HttpResponse(output.read(),
                                content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(
            progress_report.get_filename())
        return response


class ProgressReportForSemesterExcel2010View(CuratorOnlyMixin,
                                             ProgressReportForSemesterMixin,
                                             generic.base.View):
    http_method_names = ['get']

    def generate_response(self, progress_report):
        output = io.BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        format_bold = workbook.add_format({'bold': True})
        for index, header in enumerate(progress_report.headers):
            worksheet.write(0, index, header, format_bold)

        for row_index, raw_row in enumerate(progress_report.data, start=1):
            row = progress_report.export_row(raw_row)
            for col_index, value in enumerate(row):
                value = "" if value is None else force_text(value)
                worksheet.write(row_index, col_index, force_text(value))

        workbook.close()
        output.seek(0)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response = HttpResponse(output.read(), content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename="{}.xlsx"'.format(
            progress_report.get_filename())
        return response


class TotalStatisticsView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        current_year, season = get_current_semester_pair()
        start_semester_index = get_term_index(2011, Semester.TYPES.autumn)
        end_semester_index = get_term_index(current_year, season)
        semesters = Semester.objects.filter(index__gte=start_semester_index, index__lte=end_semester_index)
        # Ok, additional query for counting acceptances due to no FK on enrollment_year field. Append it to autumn season
        query = (CSCUser.objects.exclude(enrollment_year__isnull=True)
                       .values("enrollment_year")
                       .annotate(acceptances=Count("enrollment_year"))
                       .order_by("enrollment_year"))
        acceptances = defaultdict(int)
        for row in query:
            acceptances[row["enrollment_year"]] = row["acceptances"]

        query = (CSCUser.objects.exclude(graduation_year__isnull=True)
                       .values("graduation_year")
                       .annotate(graduated=Count("graduation_year"))
                       .order_by("graduation_year"))
        graduated = defaultdict(int)
        for row in query:
            graduated[row["graduation_year"]] = row["graduated"]
        # TODO: graduated and acceptances in 1 query with Django ORM?

        # FIXME: Expressional conditions don't group by items?
        # Stats for expelled students
        query = (CSCUserStatusLog.objects.values("semester")
                 .annotate(expelled=Count("student", distinct=True))
                 .filter(status=STUDENT_STATUS.expelled)
                 .order_by("status"))
        expelled = defaultdict(int)
        for row in query:
            expelled[row["semester"]] = row["expelled"]
        # TODO: Investigate how to aggregate stats for expelled and will_graduate in 1 query

        # Stats for expelled students
        query = (CSCUserStatusLog.objects
                 .values("semester")
                 .annotate(will_graduate=Count("student", distinct=True))
                 .filter(status=STUDENT_STATUS.will_graduate)
                 .order_by("status"))
        will_graduate = defaultdict(int)
        for row in query:
            will_graduate[row["semester"]] = row["will_graduate"]

        statistics = OrderedDict()
        for semester in semesters:
            acceptances_cnt, graduated_cnt = 0, 0
            if semester.type == Semester.TYPES.autumn:
                acceptances_cnt = acceptances[semester.year]
            elif semester.type == Semester.TYPES.spring:
                graduated_cnt = graduated[semester.year]
            statistics[semester.pk] = {
                "semester": semester,
                "acceptances": acceptances_cnt,
                "graduated": graduated_cnt,
                "expelled": expelled[semester.pk],
                "will_graduate": will_graduate[semester.pk],
            }
        print(statistics)


        return HttpResponse("<html><body>body tag should be returned</body></html>", content_type='text/html; charset=utf-8')
