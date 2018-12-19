# -*- coding: utf-8 -*-

import itertools
from collections import OrderedDict, defaultdict
from typing import NamedTuple

from django.conf import settings
from django.contrib import messages
from django.core.management import CommandError
from django.core.management import call_command
from django.db.models import Count, Prefetch
from django.http import HttpResponse, HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from vanilla import TemplateView

from api.permissions import CuratorAccessPermission
from core.templatetags.core_tags import tex
from admission.models import Campaign, Interview
from admission.reports import AdmissionReport
from learning.models import StudyProgram, \
    StudyProgramCourseGroup, Enrollment
from courses.models import Course, Semester
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester, WillGraduateStatsReport
from learning.settings import FOUNDATION_YEAR, CENTER_FOUNDATION_YEAR, \
    AcademicDegreeYears, StudentStatuses, \
    GradeTypes
from courses.settings import SemesterTypes
from courses.utils import get_current_term_pair, get_term_index, \
    get_term_by_index
from learning.viewmixins import CuratorOnlyMixin
from staff.models import Hint
from staff.serializers import UserSearchSerializer, FacesQueryParams
from surveys.models import CourseSurvey
from surveys.reports import SurveySubmissionsReport, SurveySubmissionsStats
from users.filters import UserFilter
from users.models import User, UserStatusLog


class StudentOffsetPagination(LimitOffsetPagination):
    default_limit = 500


class StudentSearchJSONView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = UserSearchSerializer
    pagination_class = StudentOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilter

    def get_queryset(self):
        return (User.objects
                .only('username', 'first_name', 'last_name', 'pk'))


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
            'curriculum_years': (User.objects
                                 .values_list('curriculum_year',
                                              flat=True)
                                 .filter(curriculum_year__isnull=False)
                                 .order_by('curriculum_year')
                                 .distinct()),
            'groups': {gid: User.roles.values[gid] for gid in
                       UserFilter.FILTERING_GROUPS},
            "status": StudentStatuses.values,
            "cnt_enrollments": range(UserFilter.ENROLLMENTS_MAX + 1)
        }
        return context


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"

    def get_context_data(self, **kwargs):
        current_term = get_current_term_pair(settings.DEFAULT_CITY_CODE)
        current_term_index = get_term_index(current_term.year, current_term.type)
        prev_term_year, prev_term = get_term_by_index(current_term_index - 1)
        context = {
            "current_term": current_term,
            "prev_term": {"year": prev_term_year, "type": prev_term},
            "campaigns": Campaign.objects.order_by("-city__name", "-year"),
            "center_branches": settings.CITIES
        }
        return context


class StudentsDiplomasStatsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas_stats.html"
    BAD_GRADES = [GradeTypes.UNSATISFACTORY, GradeTypes.NOT_GRADED]

    def get_context_data(self, city_code, **kwargs):
        filters = {
            "city_id": city_code,
            "status": StudentStatuses.WILL_GRADUATE
        }
        students = User.objects.students_info(filters=filters)

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
            degree_year = AcademicDegreeYears.BACHELOR_SPECIALITY_1
            if s.uni_year_at_enrollment == degree_year:
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
            s.pass_open_courses = sum(e.course.is_open for e in s.enrollments
                                      if e.grade not in self.BAD_GRADES)
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
                                                   SemesterTypes.AUTUMN)
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
                if enrollment.course.semester.type == SemesterTypes.SUMMER:
                    continue
                if enrollment.grade in self.BAD_GRADES:
                    failed_courses += 1
                    continue
                courses_by_term[enrollment.course.semester_id] += 1
                total_passed_courses += 1
                if enrollment.grade == GradeTypes.EXCELLENT:
                    excellent_total += 1
                elif enrollment.grade == GradeTypes.GOOD:
                    good_total += 1
                unique_courses.add(enrollment.course.meta_course)
                total_hours += enrollment.course.courseclass_set.count() * 1.5
                for teacher in enrollment.course.teachers.all():
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
        context = {
            'city': settings.CITIES[city_code],
            'less_failed_courses': less_failed_courses,
            'most_failed_courses': most_failed_courses,
            'all_three_practicies_are_internal': all_three_practicies_are_internal,
            'passed_practicies_in_first_two_years': passed_practicies_in_first_two_years,
            'passed_internal_practicies_in_first_two_years': passed_internal_practicies_in_first_two_years,
            'finished_two_or_more_programs': finished_two_or_more_programs,
            'by_enrollment_year': dict(by_enrollment_year),
            'enrolled_on_first_course': enrolled_on_first_course,
            'most_courses_students': most_courses_students,
            'most_courses_in_term_students': most_courses_in_term_students,
            'most_open_courses_students': most_open_courses_students,
            'students': students,
            "unique_teachers_count": len(unique_teachers),
            "total_hours": int(total_hours),
            "unique_courses": unique_courses, "good_total": good_total,
            "excellent_total": excellent_total,
            "total_passed_courses": total_passed_courses,
            "unique_projects": unique_projects
        }
        return context


class StudentsDiplomasTexView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, city_code, **kwargs):
        filters = {"city_id": city_code}
        students = ProgressReportForDiplomas.get_queryset(filters=filters)

        class DiplomaCourse(NamedTuple):
            type: str
            name: str
            teachers: str
            final_grade: str
            class_count: int = 0

        def is_project_active(ps):
            return (not ps.project.is_external and
                    not ps.project.canceled and
                    ps.final_grade != GradeTypes.NOT_GRADED and
                    ps.final_grade != GradeTypes.UNSATISFACTORY)

        for student in students:
            student.projects_through = list(filter(is_project_active,
                                                   student.projects_through))
            courses = []
            for e in student.enrollments:
                course = DiplomaCourse(
                    type="course",
                    name=tex(e.course.meta_course.name),
                    teachers=", ".join(t.get_abbreviated_name() for t in
                                       e.course.teachers.all()),
                    final_grade=str(e.grade_honest).lower(),
                    class_count=e.course.courseclass_set.count() * 2
                )
                courses.append(course)
            for c in student.shads:
                course = DiplomaCourse(
                    type="shad",
                    name=tex(c.name),
                    teachers=c.teachers,
                    final_grade=str(c.grade_display).lower(),
                )
                courses.append(course)
            courses.sort(key=lambda c: c.name)
            student.courses = courses
            delattr(student, "enrollments")
            delattr(student, "shads")

        context = {
            "city": settings.CITIES[city_code],
            "students": students
        }
        return context


class StudentsDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, city_code, *args, **kwargs):
        qs_filters = {
            "filters": {"city_id": city_code}
        }
        progress_report = ProgressReportForDiplomas(request=request,
                                                    qs_filters=qs_filters)
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
                raise ValueError("ProgressReportForSemester: Wrong year format")
            term_type = self.kwargs['term_type']
            if term_type not in SemesterTypes.values:
                raise ValueError("ProgressReportForSemester: Wrong term format")
            filters = {"year": term_year, "type": term_type}
            semester = get_object_or_404(Semester, **filters)
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        progress_report = ProgressReportForSemester(semester,
                                                    honest_grade_system=True,
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


class WillGraduateStatsReportView(CuratorOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, *args, output_format, **kwargs):
        report = WillGraduateStatsReport()
        if output_format == "csv":
            return report.output_csv()
        elif output_format == "xlsx":
            return report.output_xlsx()


class HintListView(CuratorOnlyMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "staff/warehouse.html"

    def get_queryset(self):
        return Hint.objects.order_by("sort")


class StudentFacesView(CuratorOnlyMixin, TemplateView):
    """Show students faces with names to memorize newbies"""
    template_name = "staff/student_faces.html"

    def get(self, request, *args, **kwargs):
        query_params = FacesQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        city_code = query_params.validated_data.get('city')
        if not city_code:
            # FIXME: add to util
            city_code = getattr(self.request.user, "city_id",
                                settings.DEFAULT_CITY_CODE)
        enrollment_year = query_params.validated_data.get('year')
        if not enrollment_year:
            enrollment_year, _ = get_current_term_pair(city_code)
        context = self.get_context_data(city_code, enrollment_year, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, city_code, enrollment_year, **kwargs):
        current_year, _ = get_current_term_pair(city_code)
        context = {
            'students': self.get_queryset(city_code, enrollment_year),
            "years": reversed(range(CENTER_FOUNDATION_YEAR, current_year + 1)),
            "current_year": enrollment_year,
            "current_city": city_code
        }
        return context

    def get_template_names(self):
        if "print" in self.request.GET:
            self.template_name = "staff/student_faces_printable.html"
        return super(StudentFacesView, self).get_template_names()

    def get_queryset(self, city_code, enrollment_year):
        groups = [User.roles.STUDENT_CENTER, User.roles.VOLUNTEER]
        qs = (User.objects
              .filter(groups__in=groups,
                      city_id=city_code,
                      enrollment_year=enrollment_year)
              .distinct()
              .prefetch_related("groups"))
        if "print" in self.request.GET:
            qs = qs.exclude(status=StudentStatuses.EXPELLED)
        return qs


class InterviewerFacesView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/interviewer_faces.html"

    def get_context_data(self, **kwargs):
        context = super(InterviewerFacesView, self).get_context_data(**kwargs)
        users = (Interview.interviewers.through
                 .objects.only("user_id")
                 .distinct()
                 .values_list("user_id", flat=True))
        qs = (User.objects
              .filter(id__in=users.all())
              .distinct())
        context['students'] = qs
        return context


class CourseParticipantsIntersectionView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/courses_intersection.html"

    def get_context_data(self, **kwargs):
        year, term = get_current_term_pair('spb')
        current_term_index = get_term_index(year, term)
        all_courses_in_term = (Course.objects
                               .filter(semester__index=current_term_index)
                               .select_related("meta_course"))
        # Get participants
        query_courses = self.request.GET.getlist('course_offerings[]', [])
        query_courses = [int(t) for t in query_courses if t]
        results = list(
            Course.objects
            .filter(pk__in=query_courses)
            .select_related("meta_course")
            .prefetch_related(
                Prefetch("enrollment_set",
                         queryset=(Enrollment.active
                                   .select_related("student")
                                   .only("pk",
                                         "course_id",
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
        start_semester_index = get_term_index(2011, SemesterTypes.AUTUMN)
        end_semester_index = get_term_index(current_year, season)
        semesters = Semester.objects.filter(index__gte=start_semester_index,
                                            index__lte=end_semester_index)
        # Ok, additional query for counting acceptances due to no FK on enrollment_year field. Append it to autumn season
        query = (User.objects.exclude(enrollment_year__isnull=True)
                 .values("enrollment_year")
                 .annotate(acceptances=Count("enrollment_year"))
                 .order_by("enrollment_year"))
        acceptances = defaultdict(int)
        for row in query:
            acceptances[row["enrollment_year"]] = row["acceptances"]

        query = (User.objects.exclude(graduation_year__isnull=True)
                 .values("graduation_year")
                 .annotate(graduated=Count("graduation_year"))
                 .order_by("graduation_year"))
        graduated = defaultdict(int)
        for row in query:
            graduated[row["graduation_year"]] = row["graduated"]
        # TODO: graduated and acceptances in 1 query with Django ORM?

        # FIXME: Expressional conditions don't group by items?
        # Stats for expelled students
        query = (UserStatusLog.objects.values("semester")
                 .annotate(expelled=Count("student", distinct=True))
                 .filter(status=StudentStatuses.EXPELLED)
                 .order_by("status"))
        expelled = defaultdict(int)
        for row in query:
            expelled[row["semester"]] = row["expelled"]
        # TODO: Investigate how to aggregate stats for expelled and will_graduate in 1 query

        # Stats for expelled students
        query = (UserStatusLog.objects
                 .values("semester")
                 .annotate(will_graduate=Count("student", distinct=True))
                 .filter(status=StudentStatuses.WILL_GRADUATE)
                 .order_by("status"))
        will_graduate = defaultdict(int)
        for row in query:
            will_graduate[row["semester"]] = row["will_graduate"]

        statistics = OrderedDict()
        for semester in semesters:
            acceptances_cnt, graduated_cnt = 0, 0
            if semester.type == SemesterTypes.AUTUMN:
                acceptances_cnt = acceptances[semester.year]
            elif semester.type == SemesterTypes.SPRING:
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


class SurveySubmissionsReportView(CuratorOnlyMixin, generic.base.View):
    FORMATS = ["csv", "xlsx"]

    def get(self, request, survey_pk, output_format, *args, **kwargs):
        if output_format not in self.FORMATS:
            return HttpResponseBadRequest(f"Supported formats {self.FORMATS}")
        query = (CourseSurvey.objects
                 .filter(pk=survey_pk)
                 .select_related("form",
                                 "course",
                                 "course__meta_course",
                                 "course__semester"))
        survey = get_object_or_404(query)
        report = SurveySubmissionsReport(survey)
        return getattr(report, f"output_{output_format}")()


class SurveySubmissionsStatsView(CuratorOnlyMixin, TemplateView):
    template_name = "staff/survey_submissions_stats.html"

    def get_context_data(self, **kwargs):
        survey_pk = self.kwargs["survey_pk"]
        query = (CourseSurvey.objects
                 .filter(pk=survey_pk)
                 .select_related("form",
                                 "course",
                                 "course__meta_course",
                                 "course__semester"))
        survey = get_object_or_404(query)
        report = SurveySubmissionsStats(survey)
        stats = report.calculate()
        return {
            "survey": survey,
            "total_submissions": stats["total_submissions"],
            "data": stats["fields"]
        }
