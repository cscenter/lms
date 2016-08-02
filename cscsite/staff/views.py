# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from collections import OrderedDict, defaultdict

from braces.views import JSONResponseMixin
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views import generic

from learning.admission.models import Campaign
from learning.admission.reports import AdmissionReport
from learning.models import Semester
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester
from learning.settings import STUDENT_STATUS, FOUNDATION_YEAR, SEMESTER_TYPES, \
    GRADES
from learning.utils import get_current_semester_pair, get_term_index, get_term_by_index
from learning.viewmixins import CuratorOnlyMixin
from staff.models import Hint
from users.models import CSCUser, CSCUserStatusLog
from users.filters import CSCUserFilter


class StudentSearchJSONView(CuratorOnlyMixin, JSONResponseMixin, generic.View):
    content_type = "application/json"
    limit = 500

    def get(self, request, *args, **kwargs):
        qs = CSCUser.objects.values('first_name', 'last_name', 'pk')
        filter_set = CSCUserFilter(request.GET, qs)
        if filter_set.empty_query:
            return JsonResponse({
                "total": 0,
                "users": [],
                "there_is_more": False,
            })
        filtered_users = list(filter_set.qs[:self.limit])
        for u in filtered_users:
            u['url'] = reverse('user_detail', args=[u['pk']])
        return JsonResponse({
            "total": len(filtered_users),
            "users": filtered_users,
            "there_is_more": len(filtered_users) > self.limit
        })


class StudentSearchView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/student_search.html"

    def get_context_data(self, **kwargs):
        context = super(StudentSearchView, self).get_context_data(**kwargs)
        context['json_api_uri'] = reverse('staff:student_search_json')
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
        context["campaigns"] = Campaign.objects.order_by("-name").all()
        return context
    template_name = "staff/exports.html"


class StudentsDiplomasStatsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas_stats.html"

    def get_context_data(self, **kwargs):
        context = super(StudentsDiplomasStatsView, self).get_context_data(
            **kwargs)
        students = ProgressReportForDiplomas.get_queryset()
        unique_teachers = set()
        total_hours = 0
        total_passed_courses = 0
        unique_projects = set()
        unique_courses = set()
        excellent_total = 0
        good_total = 0
        for s in students:
            for project in s.project_set.all():
                unique_projects.add(project)
            for enrollment in s.enrollments:
                total_passed_courses += 1
                if enrollment.grade == GRADES.excellent:
                    excellent_total += 1
                elif enrollment.grade == GRADES.good:
                    good_total += 1
                unique_courses.add(enrollment.course_offering.course)
                total_hours += enrollment.course_offering.courseclass_set.count() * 1.5
                for teacher in enrollment.course_offering.teachers.all():
                    unique_teachers.add(teacher.pk)
        context['students'] = students
        context["unique_teachers_count"] = len(unique_teachers)
        context["total_hours"] = int(total_hours)
        context["unique_courses"] = unique_courses
        context["good_total"] = good_total
        context["excellent_total"] = excellent_total
        context["total_passed_courses"] = total_passed_courses
        context["unique_projects"] = unique_projects
        return context


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
        return progress_report.output_csv()


class ProgressReportFullView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']
    output_format = None

    def get(self, request, *args, **kwargs):
        progress_report = ProgressReportFull(honest_grade_system=True,
                                             request=request)
        if self.output_format == "csv":
            return progress_report.output_csv()
        elif self.output_format == "xlsx":
            return progress_report.output_xlsx()
        else:
            raise ValueError("ProgressReportFullView: undefined output format")


class ProgressReportForSemesterView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']
    output_format = None

    def get(self, request, *args, **kwargs):
        # Validate year and term GET params
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
        if self.output_format == "csv":
            return progress_report.output_csv()
        elif self.output_format == "xlsx":
            return progress_report.output_xlsx()
        else:
            raise ValueError("ProgressReportForSemesterView: output "
                             "format not provided")


class AdmissionReportView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']
    output_format = None

    def get(self, request, *args, **kwargs):
        campaign_pk = kwargs.get("campaign_pk")
        report = AdmissionReport(campaign_pk=campaign_pk)
        if self.output_format == "csv":
            return report.output_csv()
        elif self.output_format == "xlsx":
            return report.output_xlsx()
        else:
            raise ValueError("AdmissionReportView: output format not provided")


class HintListView(CuratorOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "staff/warehouse.html"

    def get_queryset(self):
        return Hint.objects.order_by("sort")


# XXX: Not implemented
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
