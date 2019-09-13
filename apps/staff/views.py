# -*- coding: utf-8 -*-

from collections import defaultdict
from typing import NamedTuple

from django.conf import settings
from django.contrib import messages
from django.core.management import CommandError
from django.core.management import call_command
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic, View
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from vanilla import TemplateView

import core.utils
from admission.models import Campaign, Interview
from admission.reports import AdmissionReport
from api.permissions import CuratorAccessPermission
from core.models import Branch
from core.settings.base import FOUNDATION_YEAR, CENTER_FOUNDATION_YEAR, \
    DEFAULT_BRANCH_CODE
from core.templatetags.core_tags import tex
from core.urls import reverse
from courses.constants import SemesterTypes
from courses.models import Course, Semester
from courses.utils import get_current_term_pair, get_term_index, \
    get_term_by_index
from learning.gradebook.views import GradeBookListBaseView
from learning.models import Enrollment, Invitation
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester, WillGraduateStatsReport, \
    ProgressReportForInvitation, DataFrameResponse
from learning.settings import AcademicDegreeYears, StudentStatuses, \
    GradeTypes, Branches
from staff.forms import GraduationForm
from staff.models import Hint
from staff.serializers import UserSearchSerializer, FacesQueryParams
from surveys.models import CourseSurvey
from surveys.reports import SurveySubmissionsReport, SurveySubmissionsStats
from users.constants import Roles
from users.filters import UserFilter
from users.mixins import CuratorOnlyMixin
from users.models import User


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
                .only('username', 'first_name', 'last_name', 'pk')
                .order_by('last_name', 'first_name'))


class StudentSearchView(CuratorOnlyMixin, TemplateView):
    template_name = "staff/student_search.html"

    def get_context_data(self, **kwargs):
        # TODO: rewrite with django-filters
        branches = (Branch.objects
                    .filter(site_id=settings.SITE_ID)
                    .order_by('order'))
        context = {
            'json_api_uri': reverse('staff:student_search_json'),
            'branches': {b.pk: b.name for b in branches},
            'curriculum_years': (User.objects
                                 .values_list('curriculum_year',
                                              flat=True)
                                 .filter(curriculum_year__isnull=False)
                                 .order_by('curriculum_year')
                                 .distinct()),
            'groups': UserFilter.get_filters()['groups'].choices,
            "status": StudentStatuses.values,
            "cnt_enrollments": range(UserFilter.ENROLLMENTS_MAX + 1)
        }
        return context


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"

    def get_context_data(self, **kwargs):
        current_term = get_current_term_pair()
        current_term_index = get_term_index(current_term.year, current_term.type)
        prev_term_year, prev_term = get_term_by_index(current_term_index - 1)
        graduation_form = GraduationForm()
        graduation_form.helper.form_action = reverse('staff:create_alumni_profiles')
        context = {
            "alumni_profiles_form": graduation_form,
            "current_term": current_term,
            "prev_term": {"year": prev_term_year, "type": prev_term},
            "campaigns": (Campaign.objects
                          .select_related("branch")
                          .order_by("-branch__name", "-year")),
            "branches": Branch.objects.filter(site_id=settings.SITE_ID)
        }
        return context


class StudentsDiplomasStatsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas_stats.html"
    BAD_GRADES = [GradeTypes.UNSATISFACTORY, GradeTypes.NOT_GRADED]

    def get_context_data(self, branch_id, **kwargs):
        students = (User.objects
                    .has_role(Roles.STUDENT,
                              Roles.GRADUATE,
                              Roles.VOLUNTEER)
                    .student_progress()
                    .filter(branch_id=branch_id,
                            status=StudentStatuses.WILL_GRADUATE))

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
            if s.graduate_profile and len(s.graduate_profile.academic_disciplines.all()) >= 2:
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
            for ps in s.projects_progress:
                if ps.final_grade in self.BAD_GRADES or ps.project.is_canceled:
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
            "branch": Branch.objects.get(pk=branch_id),
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


# FIXME: можно ли это объединить с csv/xlsx импортами?
class StudentsDiplomasTexView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, branch_id, **kwargs):
        students = (ProgressReportForDiplomas().get_queryset()
                    .filter(branch_id=branch_id))

        class DiplomaCourse(NamedTuple):
            type: str
            name: str
            teachers: str
            final_grade: str
            class_count: int = 0

        def is_project_active(ps):
            return (not ps.project.is_external and
                    not ps.project.is_canceled and
                    ps.final_grade != GradeTypes.NOT_GRADED and
                    ps.final_grade != GradeTypes.UNSATISFACTORY)

        for student in students:
            student.projects_progress = list(filter(is_project_active,
                                                    student.projects_progress))
            courses = []
            for e in student.enrollments_progress:
                course = DiplomaCourse(
                    type="course",
                    name=tex(e.course.meta_course.name),
                    teachers=", ".join(t.get_abbreviated_name() for t in
                                       e.course.teachers.all()),
                    final_grade=str(e.grade_honest).lower(),
                    # FIXME: db hit for each record
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
            delattr(student, "enrollments_progress")
            delattr(student, "shads")

        context = {
            "branch": Branch.objects.get(pk=branch_id),
            "students": students
        }
        return context


class StudentsDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, branch_id, *args, **kwargs):
        report = ProgressReportForDiplomas()
        df = report.generate(report.get_queryset().filter(branch_id=branch_id))
        return DataFrameResponse.as_csv(df, report.get_filename())


class ProgressReportFullView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, *args, **kwargs):
        report = ProgressReportFull(grade_getter="grade_honest")
        if output_format == "csv":
            return DataFrameResponse.as_csv(report.generate(),
                                            report.get_filename())
        elif output_format == "xlsx":
            return report.output_xlsx()
        else:
            return HttpResponseBadRequest(f"{output_format} format "
                                          f"is not supported")


class ProgressReportForSemesterView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, *args, **kwargs):
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
        report = ProgressReportForSemester(semester)
        filename = report.get_filename()
        if output_format == "csv":
            return DataFrameResponse.as_csv(report.generate(), filename)
        elif output_format == "xlsx":
            return DataFrameResponse.as_xlsx(report.generate(), filename)
        else:
            return HttpResponseBadRequest(f"{output_format} format "
                                          f"is not supported")


class InvitationStudentsProgressReportView(CuratorOnlyMixin, View):
    def get(self, request, output_format, invitation_id, *args, **kwargs):
        invitation = get_object_or_404(Invitation.objects
                                       .filter(pk=invitation_id))
        progress_report = ProgressReportForInvitation(invitation)
        if output_format == "csv":
            return progress_report.output_csv()
        elif output_format == "xlsx":
            return progress_report.output_xlsx()
        else:
            return HttpResponseBadRequest(f"{output_format} format "
                                          f"is not supported")


class AdmissionReportView(CuratorOnlyMixin, generic.base.View):
    FORMATS = ('csv', 'xlsx')

    def get(self, request, campaign_id, output_format, **kwargs):
        if output_format not in self.FORMATS:
            return HttpResponseBadRequest(f"Supported formats {self.FORMATS}")
        campaign = get_object_or_404(Campaign.objects.filter(pk=campaign_id))
        report = AdmissionReport(campaign=campaign)
        if output_format == "csv":
            return report.output_csv()
        elif output_format == "xlsx":
            return report.output_xlsx()


class WillGraduateStatsReportView(CuratorOnlyMixin, generic.base.View):
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
    """Photo + names to memorize newbies"""
    template_name = "staff/student_faces.html"

    def get(self, request, *args, **kwargs):
        query_params = FacesQueryParams(data=request.GET)
        if not query_params.is_valid():
            return HttpResponseRedirect(request.path)
        branch_code = query_params.validated_data.get('branch',
                                                      DEFAULT_BRANCH_CODE)
        branch = get_object_or_404(Branch.objects
                                   .filter(code=branch_code,
                                           site_id=settings.SITE_ID))
        enrollment_year = query_params.validated_data.get('year')
        if not enrollment_year:
            enrollment_year, _ = get_current_term_pair(branch.get_timezone())
        context = self.get_context_data(branch, enrollment_year, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, branch, enrollment_year, **kwargs):
        current_year, _ = get_current_term_pair(branch.get_timezone())
        context = {
            'students': self.get_queryset(branch, enrollment_year),
            "years": reversed(range(CENTER_FOUNDATION_YEAR, current_year + 1)),
            "current_year": enrollment_year,
            "current_branch": branch,
            "branches": Branches
        }
        return context

    def get_template_names(self):
        if "print" in self.request.GET:
            self.template_name = "staff/student_faces_printable.html"
        return super(StudentFacesView, self).get_template_names()

    def get_queryset(self, branch, enrollment_year):
        roles = (Roles.STUDENT, Roles.VOLUNTEER)
        qs = (User.objects
              .has_role(*roles)
              .filter(branch=branch,
                      enrollment_year=enrollment_year)
              .distinct('last_name', 'first_name', 'pk')
              .order_by('last_name', 'first_name', 'pk')
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
        year, term = get_current_term_pair()
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


def autograde_projects(request):
    if not request.user.is_curator:
        return HttpResponseForbidden()
    try:
        graded = call_command('autograde_projects')
        messages.success(request, f"Операция выполнена успешно.<br>"
                                  f"Выставлено оценок: {graded}")
    except CommandError as e:
        messages.error(request, str(e))
    return HttpResponseRedirect(reverse("staff:exports"))


def create_alumni_profiles(request):
    if not request.user.is_curator:
        return HttpResponseForbidden()

    form = GraduationForm(data=request.POST)
    if form.is_valid():
        graduated_on = form.cleaned_data['graduated_on']
        try:
            cmd = call_command('create_alumni_profiles',
                               graduated_on.strftime('%d.%m.%Y'))
            messages.success(request, f"Операция выполнена успешно.")
        except CommandError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, str('Неверный формат даты выпуска'))
    return HttpResponseRedirect(reverse("staff:exports"))


class SurveySubmissionsReportView(CuratorOnlyMixin, generic.base.View):
    FORMATS = ("csv", "xlsx")

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


class GradeBookListView(CuratorOnlyMixin, GradeBookListBaseView):
    template_name = "staff/gradebook_list.html"

    def get_term_threshold(self):
        latest_term = Semester.objects.order_by("-index").first()
        term_index = latest_term.index
        if latest_term == SemesterTypes.AUTUMN:
            term_index += 1
        return term_index

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_list = list(context["semester_list"])
        if not semester_list:
            return context
        # Add stub spring term if we have only the fall term for the ongoing
        # academic year
        current = semester_list[0]
        if current.type == SemesterTypes.AUTUMN:
            term = Semester(type=SemesterTypes.SPRING, year=current.year + 1)
            term.courseofferings = []
            semester_list.insert(0, term)
        context["semester_list"] = [(a, s) for s, a in
                                    core.utils.chunks(semester_list, 2)]
        return context
