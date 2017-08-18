# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from collections import OrderedDict, defaultdict

import itertools
from braces.views import JSONResponseMixin
from django.conf import settings
from django.contrib import messages
from django.core.management import CommandError
from django.core.management import call_command
from django.urls import reverse
from django.db.models import Count, Prefetch
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views import generic
from django.utils.translation import ugettext_lazy as _
from vanilla import TemplateView

from core.models import City
from learning.admission.models import Campaign, Interview
from learning.admission.reports import AdmissionReport
from learning.models import Semester, CourseOffering, StudyProgram, \
    StudyProgramCourseGroup, Enrollment
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester
from learning.settings import STUDENT_STATUS, FOUNDATION_YEAR, SEMESTER_TYPES, \
    GRADES, CENTER_FOUNDATION_YEAR
from learning.utils import get_current_term_pair, get_term_index, get_term_by_index
from learning.viewmixins import CuratorOnlyMixin
from staff.models import Hint
from users.models import CSCUser, CSCUserStatusLog
from users.filters import UserFilter


class StudentSearchJSONView(CuratorOnlyMixin, JSONResponseMixin, generic.View):
    content_type = "application/json"
    limit = 500

    def get(self, request, *args, **kwargs):
        qs = CSCUser.objects.values('first_name', 'last_name', 'pk')
        filter_set = UserFilter(request.GET, qs)
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


class StudentSearchView(CuratorOnlyMixin, TemplateView):
    template_name = "staff/student_search.html"

    def get_context_data(self, **kwargs):
        # TODO: rewrite with django-filters
        context = {
            'json_api_uri': reverse('staff:student_search_json'),
            'cities': OrderedDict({
                'spb': 'Санкт-Петербург',
                'nsk': 'Новосибирск'
            }),
            'curriculum_years': (CSCUser.objects
                                 .values_list('curriculum_year',
                                              flat=True)
                                 .filter(curriculum_year__isnull=False)
                                 .order_by('curriculum_year')
                                 .distinct()),
            'groups': {gid: CSCUser.group[gid] for gid in
                       UserFilter.FILTERING_GROUPS},
            "status": {sid: name for sid, name in CSCUser.STATUS},
            "cnt_enrollments": range(UserFilter.ENROLLMENTS_MAX + 1)
        }
        return context


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    def get_context_data(self, **kwargs):
        context = super(ExportsView, self).get_context_data(**kwargs)
        year, term = get_current_term_pair(settings.DEFAULT_CITY_CODE)
        current_term_index = get_term_index(year, term)
        context["current_term"] = {"year": year, "type": term}
        prev_term_year, prev_term = get_term_by_index(current_term_index - 1)
        context["prev_term"] = {"year": prev_term_year, "type": prev_term}
        context["campaigns"] = Campaign.objects.order_by("-city__name", "-year")
        return context
    template_name = "staff/exports.html"


class StudentsDiplomasStatsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas_stats.html"
    BAD_GRADES = [GRADES.unsatisfactory, GRADES.not_graded]

    def get_context_data(self, **kwargs):
        context = super(StudentsDiplomasStatsView, self).get_context_data(
            **kwargs)
        students = CSCUser.objects.students_info(
            filters={"status": CSCUser.STATUS.will_graduate})

        unique_teachers = set()
        total_hours = 0
        total_passed_courses = 0
        unique_projects = set()
        unique_courses = set()
        excellent_total = 0
        good_total = 0
        most_courses_students = set()
        most_courses_in_term_students = set()
        most_open_courses_students = set()
        enrolled_on_first_course = set()
        by_enrollment_year = defaultdict(set)
        finished_two_or_more_programs = set()
        all_three_practicies_are_internal = set()
        passed_practicies_in_first_two_years = set()
        passed_internal_practicies_in_first_two_years = set()
        most_failed_courses = set()
        less_failed_courses = set()

        for s in students:
            if len(s.areas_of_study.all()) >= 2:
                finished_two_or_more_programs.add(s)
            by_enrollment_year[s.enrollment_year].add(s)
            if s.uni_year_at_enrollment == CSCUser.COURSES.BACHELOR_SPECIALITY_1 or (hasattr(s, "applicant") and s.applicant.course == CSCUser.COURSES.BACHELOR_SPECIALITY_1):
                enrolled_on_first_course.add(s)
            # Count most_courses_students
            s.passed_courses = sum(1 for e in s.enrollments if e.grade not in self.BAD_GRADES)
            s.passed_courses += sum(1 for c in s.shads if c.grade not in self.BAD_GRADES)
            if not most_courses_students:
                most_courses_students = {s}
            else:
                # FIXME: most_courses_student и most_courses_student interm
                most_courses_student = next(iter(most_courses_students))
                if s.passed_courses == most_courses_student.passed_courses:
                    most_courses_students.add(s)
                elif s.passed_courses > most_courses_student.passed_courses:
                    most_courses_students = {s}
            s.pass_open_courses = sum(e.course_offering.is_open for e in s.enrollments if e.grade not in self.BAD_GRADES)
            if not most_open_courses_students:
                most_open_courses_students.add(s)
            else:
                most_open_courses_student = next(iter(most_open_courses_students))
                if s.pass_open_courses == most_open_courses_student.pass_open_courses:
                    most_open_courses_students.add(s)
                elif s.pass_open_courses > most_open_courses_student.pass_open_courses:
                    most_open_courses_students = {s}

            internal_projects_cnt = 0
            projects_in_first_two_years_of_learning = 0
            internal_projects_in_first_two_years_of_learning = 0
            enrollment_term_index = get_term_index(s.enrollment_year,
                                                   SEMESTER_TYPES.autumn)
            for ps in s.projects_through:
                if ps.final_grade in self.BAD_GRADES or ps.project.canceled:
                    continue
                unique_projects.add(ps.project)
                internal_projects_cnt += int(not ps.project.is_external)
                if 0 <= ps.project.semester.index - enrollment_term_index <= 4:
                    projects_in_first_two_years_of_learning += 1
                    if not ps.project.is_external:
                        internal_projects_in_first_two_years_of_learning += 1
            if internal_projects_cnt == 3:
                all_three_practicies_are_internal.add(s)
            if projects_in_first_two_years_of_learning >= 3:
                passed_practicies_in_first_two_years.add(s)
            if internal_projects_in_first_two_years_of_learning >= 3:
                passed_internal_practicies_in_first_two_years.add(s)

            courses_by_term = defaultdict(int)
            failed_courses = 0
            # Add shad courses
            for c in s.shads:
                if c.grade in self.BAD_GRADES:
                    failed_courses += 1
                    continue
                courses_by_term[c.semester_id] += 1
            for enrollment in s.enrollments:
                # Skip summer courses
                if enrollment.course_offering.semester.type == SEMESTER_TYPES.summer:
                    continue
                if enrollment.grade in self.BAD_GRADES:
                    failed_courses += 1
                    continue
                courses_by_term[enrollment.course_offering.semester_id] += 1
                total_passed_courses += 1
                if enrollment.grade == GRADES.excellent:
                    excellent_total += 1
                elif enrollment.grade == GRADES.good:
                    good_total += 1
                unique_courses.add(enrollment.course_offering.course)
                total_hours += enrollment.course_offering.courseclass_set.count() * 1.5
                for teacher in enrollment.course_offering.teachers.all():
                    unique_teachers.add(teacher.pk)

            s.failed_courses = failed_courses
            if not most_failed_courses:
                most_failed_courses = {s}
            else:
                most_failed_course_student = next(iter(most_failed_courses))
                if s.failed_courses == most_failed_course_student.failed_courses:
                    most_failed_courses.add(s)
                elif s.failed_courses > most_failed_course_student.failed_courses:
                    most_failed_courses = {s}
            # Less failed courses
            if not less_failed_courses:
                less_failed_courses = {s}
            else:
                less_failed_course_student = next(iter(most_failed_courses))
                if s.failed_courses == less_failed_course_student.failed_courses:
                    less_failed_courses.add(s)
                elif s.failed_courses < less_failed_course_student.failed_courses:
                    less_failed_courses = {s}

            try:
                s.max_courses_in_term = max(courses_by_term.values())
            except ValueError:
                s.max_courses_in_term = 0
            if not most_courses_in_term_students:
                most_courses_in_term_students = {s}
            else:
                most_courses_in_term_student = next(iter(most_courses_in_term_students))
                if s.max_courses_in_term == most_courses_in_term_student.max_courses_in_term:
                    most_courses_in_term_students.add(s)
                elif s.max_courses_in_term > most_courses_in_term_student.max_courses_in_term:
                    most_courses_in_term_students = {s}
        context['less_failed_courses'] = less_failed_courses
        context['most_failed_courses'] = most_failed_courses
        context['all_three_practicies_are_internal'] = all_three_practicies_are_internal
        context['passed_practicies_in_first_two_years'] = passed_practicies_in_first_two_years
        context['passed_internal_practicies_in_first_two_years'] = passed_internal_practicies_in_first_two_years
        context['finished_two_or_more_programs'] = finished_two_or_more_programs
        context['by_enrollment_year'] = dict(by_enrollment_year)
        context['enrolled_on_first_course'] = enrolled_on_first_course
        context['most_courses_students'] = most_courses_students
        context['most_courses_in_term_students'] = most_courses_in_term_students
        context['most_open_courses_students'] = most_open_courses_students
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
        students = ProgressReportForDiplomas.get_queryset()

        # FIXME: Investigate can I update queryset instead?
        def is_project_active(ps):
            return (not ps.project.is_external and
                    not ps.project.canceled and
                    ps.final_grade != GRADES.not_graded and
                    ps.final_grade != GRADES.unsatisfactory)

        for student in students:
            student.projects_through = list(filter(is_project_active,
                                                   student.projects_through))
        context['students'] = students
        return context


class StudentsDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        progress_report = ProgressReportForDiplomas(request=request)
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
        campaign = get_object_or_404(Campaign.objects.filter(pk=campaign_pk))
        report = AdmissionReport(campaign=campaign)
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


def debug_test_job(id):
    from django.apps import apps
    CourseClass = apps.get_model('learning', 'CourseClass')
    instance = CourseClass.objects.get(pk=1660)
    return instance.pk


class StudentFacesView(CuratorOnlyMixin, generic.TemplateView):
    """Show students faces with names to memorize newbies"""
    template_name = "staff/student_faces.html"

    def get_template_names(self):
        if "print" in self.request.GET:
            self.template_name = "staff/student_faces_printable.html"
        return super(StudentFacesView, self).get_template_names()

    def get_context_data(self, **kwargs):
        # FIXME: add test job, remove after debug!
        import django_rq
        queue = django_rq.get_queue('default')
        queue.enqueue(debug_test_job, 1660)
        context = super(StudentFacesView, self).get_context_data(**kwargs)
        enrollment_year = self.request.GET.get("year", None)
        year, current_term = get_current_term_pair('spb')
        try:
            enrollment_year = int(enrollment_year)
        except (TypeError, ValueError):
            # TODO: make redirect
            enrollment_year = year
        qs = (CSCUser.objects.filter(
            groups__in=[CSCUser.group.STUDENT_CENTER,
                        CSCUser.group.VOLUNTEER],
            enrollment_year=enrollment_year).distinct())
        if "print" in self.request.GET:
            qs = qs.exclude(status=CSCUser.STATUS.expelled)
        context['students'] = qs
        context["years"] = reversed(range(CENTER_FOUNDATION_YEAR, year + 1))
        context["current_year"] = enrollment_year
        return context


class InterviewerFacesView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/interviewer_faces.html"

    def get_context_data(self, **kwargs):
        context = super(InterviewerFacesView, self).get_context_data(**kwargs)
        users = (Interview.interviewers.through
                 .objects.only("cscuser_id")
                 .distinct()
                 .values_list("cscuser_id", flat=True))
        qs = (CSCUser.objects
              .filter(id__in=users.all())
              .distinct())
        context['students'] = qs
        return context


class CourseParticipantsIntersectionView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/courses_intersection.html"

    def get_context_data(self, **kwargs):
        year, term = get_current_term_pair('spb')
        current_term_index = get_term_index(year, term)
        all_courses_in_term = (CourseOffering.objects
                               .filter(semester__index=current_term_index)
                               .select_related("course"))
        # Get participants
        query_courses = self.request.GET.getlist('course_offerings[]', [])
        query_courses = [int(t) for t in query_courses if t]
        results = list(
            CourseOffering.objects
            .filter(pk__in=query_courses)
            .select_related("course")
            .prefetch_related(
                Prefetch("enrollment_set",
                         queryset=(Enrollment.active
                                   .select_related("student")
                                   .only("pk",
                                         "course_offering_id",
                                         "student_id",
                                         "student__username",
                                         "student__first_name",
                                         "student__last_name",
                                         "student__patronymic")))
            ))
        if len(results) > 1:
            first_course, second_course = (
                {e.student_id for e in co.enrollment_set.all()} for co in results)
            intersection = first_course.intersection(second_course)
        else:
            intersection = set()
        context = {
            'course_offerings': all_courses_in_term,
            'intersection': intersection,
            'current_term': "{} {}".format(_(term), year),
            'results': results,
            'query': {
                'course_offerings': query_courses
            }
        }
        return context


# XXX: Not implemented
# TODO: remove
class TotalStatisticsView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        current_year, season = get_current_term_pair('spb')
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


def autograde_projects(request):
    if not request.user.is_curator:
        return HttpResponseForbidden()
    try:
        processed = call_command('autograde_projects')
        messages.success(request, "Операция выполнена успешно. "
                                  "Обработано: {}".format(processed))
    except CommandError as e:
        messages.error(request, str(e))
    return HttpResponseRedirect(reverse("staff:exports"))


class SyllabusView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/syllabus.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        syllabus = (StudyProgram.objects
                    .filter(year=2017)
                    .select_related("area")
                    .prefetch_related(
                        Prefetch(
                            'course_groups',
                            queryset=(StudyProgramCourseGroup
                                      .objects
                                      .prefetch_related("courses")),
                        ))
                    .order_by("city_id", "area__name_ru"))
        context["programs"] = self.group_programs_by_city(syllabus)
        # TODO: validate entry city
        context["selected_city"] = self.request.GET.get('city', 'spb')
        return context

    def group_programs_by_city(self, syllabus):
        grouped = {}
        for city_id, g in itertools.groupby(syllabus,
                                            key=lambda sp: sp.city_id):
            grouped[city_id] = list(g)
        return grouped
