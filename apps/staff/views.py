import csv
import datetime
from collections import defaultdict

from django.utils import timezone, formats
from django.utils.safestring import mark_safe
from django_filters import FilterSet
from django_filters.views import BaseFilterView, FilterView
from rest_framework import serializers
from vanilla import TemplateView

from django.conf import settings
from django.contrib import messages
from django.core.management import CommandError, call_command
from django.db.models import Count, Prefetch
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import Http404, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_list_or_404, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views import View, generic

import core.utils
from admission.models import Campaign, Interview
from admission.reports import (
    AdmissionApplicantsCampaignReport,
    AdmissionExamReport,
    generate_admission_interviews_report, AdmissionApplicantsYearReport,
)
from core.http import HttpRequest
from core.models import Branch
from core.typings import assert_never
from core.urls import reverse
from core.utils import bucketize
from courses.constants import SemesterTypes
from courses.models import Course, Semester, CourseDurations
from courses.utils import get_current_term_pair, get_term_index
from learning.gradebook.views import GradeBookListBaseView
from learning.models import Enrollment, GraduateProfile, Invitation
from learning.reports import (
    FutureGraduateDiplomasReport,
    OfficialDiplomasReport,
    ProgressReportForInvitation,
    ProgressReportForSemester,
    ProgressReportFull,
    WillGraduateStatsReport,
    dataframe_to_response,
)
from learning.settings import AcademicDegreeLevels, GradeTypes, StudentStatuses
from projects.constants import ProjectGradeTypes
from staff.filters import EnrollmentInvitationFilter, StudentProfileFilter, StudentAcademicDisciplineLogFilter, \
    StudentStatusLogFilter
from staff.forms import BadgeNumberFromCSVForm, GraduationForm, MergeUsersForm
from staff.models import Hint
from staff.tex import generate_tex_student_profile_for_diplomas
from study_programs.models import AcademicDiscipline
from surveys.models import CourseSurvey
from surveys.reports import SurveySubmissionsReport, SurveySubmissionsStats
from users.filters import StudentFilter
from users.mixins import CuratorOnlyMixin
from users.models import PartnerTag, StudentProfile, StudentTypes, User, StudentAcademicDisciplineLog, StudentStatusLog
from users.services import (
    badge_number_from_csv,
    create_graduate_profiles,
    get_graduate_profile,
    get_student_progress, merge_users,
)


class StudentSearchCSVView(CuratorOnlyMixin, BaseFilterView):
    context_object_name = "applicants"
    model = StudentProfile
    filterset_class = StudentFilter

    def get_queryset(self):
        return StudentProfile.objects.select_related(
            "user", "branch", "graduate_profile"
        )

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)

        if (
            not self.filterset.is_bound
            or self.filterset.is_valid()
            or not self.get_strict()
        ):
            queryset = self.filterset.qs
        else:
            queryset = self.filterset.queryset.none()
        report = ProgressReportFull(grade_getter="grade_honest")
        custom_qs = report.get_queryset(base_queryset=queryset)
        df = report.generate(queryset=custom_qs)
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        file_name = f"sheet_{today}"
        return dataframe_to_response(df, "csv", file_name)


class StudentSearchView(CuratorOnlyMixin, TemplateView):
    template_name = "lms/staff/student_search.html"

    def get_context_data(self, **kwargs):
        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        context = {
            "json_api_uri": reverse("staff:student_search_json"),
            "branches": {b.pk: b.name for b in branches},
            "curriculum_years": (
                StudentProfile.objects.filter(
                    site=self.request.site, year_of_curriculum__isnull=False
                )
                .values_list("year_of_curriculum", flat=True)
                .order_by("year_of_curriculum")
                .distinct()
            ),
            "admission_years": (
                StudentProfile.objects.filter(
                    site=self.request.site, year_of_admission__isnull=False
                )
                .values_list("year_of_admission", flat=True)
                .order_by("year_of_admission")
                .distinct()
            ),
            "types": StudentTypes.choices,
            "academic_disciplines": AcademicDiscipline.objects.all(),
            "partner_tags": PartnerTag.objects.all(),
            "status": StudentStatuses.values,
            "cnt_enrollments": range(StudentFilter.ENROLLMENTS_MAX + 1),
            "is_paid_basis": [("1", "Да"), ("0", "Нет")],
            "uni_graduation_year": (
                StudentProfile.objects.filter(
                    site=self.request.site,
                    graduation_year__isnull=False,
                    graduate_without_diploma=True
                )
                .values_list("graduation_year", flat=True)
                .order_by("graduation_year")
                .distinct()
            )
        }
        return context


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"

    def get_context_data(self, **kwargs):
        current_term = get_current_term_pair()
        prev_term = current_term.get_prev()
        graduation_form = GraduationForm()
        graduation_form.helper.form_action = reverse("staff:create_alumni_profiles")
        merge_users_form = MergeUsersForm()
        badge_number_from_csv_form = BadgeNumberFromCSVForm()
        official_diplomas_dates = (
            GraduateProfile.objects.for_site(self.request.site)
            .with_official_diploma()
            .distinct("diploma_issued_on")
            .order_by("-diploma_issued_on")
            .values_list("diploma_issued_on", flat=True)
        )
        branches = Branch.objects.filter(site_id=settings.SITE_ID)
        context = {
            "alumni_profiles_form": graduation_form,
            "merge_users_form": merge_users_form,
            "badge_number_from_csv_form": badge_number_from_csv_form,
            "current_term": current_term,
            "prev_term": {"year": prev_term.year, "type": prev_term.type},
            "campaigns": (
                Campaign.objects.filter(branch__in=branches)
                .select_related("branch")
                .order_by("-year", "branch__name")
            ),
            "years": Campaign.objects.filter(branch__in=branches).values_list('year', flat=True).distinct().order_by('-year'),
            "branches": branches,
            "official_diplomas_dates": official_diplomas_dates,
        }
        return context


class FutureGraduateStatsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas_stats.html"
    BAD_GRADES = GradeTypes.unsatisfactory_grades
    BAD_PROJECT_GRADES = [
        ProjectGradeTypes.UNSATISFACTORY,
        ProjectGradeTypes.NOT_GRADED,
    ]

    def get_context_data(self, branch_id, **kwargs):
        student_profiles = (
            StudentProfile.objects.filter(
                type=StudentTypes.REGULAR,
                branch_id=branch_id,
                status=StudentStatuses.WILL_GRADUATE,
            )
            .select_related("user")
            .order_by("user__last_name", "user__first_name", "user_id")
        )
        progress = get_student_progress(student_profiles)
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
        by_year_of_admission = defaultdict(set)
        finished_two_or_more_programs = set()
        all_three_practicies_are_internal = set()
        passed_practicies_in_first_two_years = set()
        passed_internal_practicies_in_first_two_years = set()
        most_failed_courses = set()
        less_failed_courses = set()

        for student_profile in student_profiles:
            s = student_profile.user
            enrollments = progress[s.id].get("enrollments", [])
            projects = progress[s.id].get("projects", [])
            shad = progress[s.id].get("shad", [])
            graduate_profile = get_graduate_profile(student_profile)
            if (
                graduate_profile
                and len(graduate_profile.academic_disciplines.all()) >= 2
            ):
                finished_two_or_more_programs.add(s)
            by_year_of_admission[student_profile.year_of_admission].add(student_profile)
            degree_year = AcademicDegreeLevels.BACHELOR_SPECIALITY_1
            if student_profile.level_of_education_on_admission == degree_year:
                enrolled_on_first_course.add(s)
            # Count most_courses_students
            s.passed_courses = sum(
                1 for e in enrollments if e.grade not in self.BAD_GRADES
            )
            s.passed_courses += sum(1 for c in shad if c.grade not in self.BAD_GRADES)
            if not most_courses_students:
                most_courses_students = {s}
            else:
                most_courses_student = next(iter(most_courses_students))
                if s.passed_courses == most_courses_student.passed_courses:
                    most_courses_students.add(s)
                elif s.passed_courses > most_courses_student.passed_courses:
                    most_courses_students = {s}
            s.pass_open_courses = sum(
                e.course.is_club_course
                for e in enrollments
                if e.grade not in self.BAD_GRADES
            )
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
            enrollment_term_index = get_term_index(
                student_profile.year_of_admission, SemesterTypes.AUTUMN
            )
            for ps in projects:
                if ps.final_grade in self.BAD_PROJECT_GRADES or ps.project.is_canceled:
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
            for c in shad:
                if c.grade in self.BAD_GRADES:
                    failed_courses += 1
                    continue
                courses_by_term[c.semester_id] += 1
            for enrollment in enrollments:
                # Skip summer courses
                if enrollment.course.semester.type == SemesterTypes.SUMMER:
                    continue
                if enrollment.grade in self.BAD_GRADES:
                    failed_courses += 1
                    continue
                courses_by_term[enrollment.course.semester_id] += 1
                total_passed_courses += 1
                if enrollment.grade in GradeTypes.excellent_grades:
                    excellent_total += 1
                elif enrollment.grade in GradeTypes.good_grades:
                    good_total += 1
                unique_courses.add(enrollment.course.meta_course)
                total_hours += enrollment.course.courseclass_set.count() * 1.5
                for course_teacher in enrollment.course.course_teachers.all():
                    unique_teachers.add(course_teacher.teacher_id)

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
                if (
                    s.max_courses_in_term
                    == most_courses_in_term_student.max_courses_in_term
                ):
                    most_courses_in_term_students.add(s)
                elif (
                    s.max_courses_in_term
                    > most_courses_in_term_student.max_courses_in_term
                ):
                    most_courses_in_term_students = {s}
        context = {
            "branch": Branch.objects.get(pk=branch_id),
            "less_failed_courses": less_failed_courses,
            "most_failed_courses": most_failed_courses,
            "all_three_practicies_are_internal": all_three_practicies_are_internal,
            "passed_practicies_in_first_two_years": passed_practicies_in_first_two_years,
            "passed_internal_practicies_in_first_two_years": passed_internal_practicies_in_first_two_years,
            "finished_two_or_more_programs": finished_two_or_more_programs,
            "by_enrollment_year": dict(by_year_of_admission),
            "enrolled_on_first_course": enrolled_on_first_course,
            "most_courses_students": most_courses_students,
            "most_courses_in_term_students": most_courses_in_term_students,
            "most_open_courses_students": most_open_courses_students,
            "student_profiles": student_profiles,
            "unique_teachers_count": len(unique_teachers),
            "total_hours": int(total_hours),
            "unique_courses": unique_courses,
            "good_total": good_total,
            "excellent_total": excellent_total,
            "total_passed_courses": total_passed_courses,
            "unique_projects": unique_projects,
        }
        return context


class FutureGraduateDiplomasTeXView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, branch_id, **kwargs):
        branch = Branch.objects.get(pk=branch_id)
        report = FutureGraduateDiplomasReport(branch)
        student_profiles = report.get_queryset()
        students = (sp.user for sp in student_profiles)
        courses_qs = report.get_courses_queryset(students).annotate(
            classes_total=Count("courseclass")
        )
        courses = {c.pk: c for c in courses_qs}

        diploma_student_profiles = [
            generate_tex_student_profile_for_diplomas(sp, courses)
            for sp in student_profiles
        ]

        context = {"branch": branch, "students": diploma_student_profiles}
        return context


class FutureGraduateDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, branch_id, *args, **kwargs):
        branch = get_object_or_404(Branch.objects.filter(pk=branch_id))
        report = FutureGraduateDiplomasReport(branch)
        df = report.generate()
        today = datetime.datetime.now()
        file_name = "diplomas_{}".format(today.year)
        return dataframe_to_response(df, "csv", file_name)


class ProgressReportFullView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, *args, **kwargs):
        report = ProgressReportFull(grade_getter="grade_honest")
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        file_name = f"sheet_{today}"
        return dataframe_to_response(report.generate(), output_format, file_name)


class ProgressReportForSemesterView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, *args, **kwargs):
        # Validate year and term GET params
        try:
            term_year = int(self.kwargs["term_year"])
            if term_year < settings.ESTABLISHED:
                raise ValueError("ProgressReportForSemester: Wrong year format")
            term_type = self.kwargs["term_type"]
            if term_type not in SemesterTypes.values:
                raise ValueError("ProgressReportForSemester: Wrong term format")
            filters = {"year": term_year, "type": term_type}
            semester = get_object_or_404(Semester, **filters)
        except (KeyError, ValueError):
            return HttpResponseBadRequest()
        report = ProgressReportForSemester(semester)
        file_name = "sheet_{}_{}".format(semester.year, semester.type)
        return dataframe_to_response(report.generate(), output_format, file_name)


class EnrollmentInvitationListView(CuratorOnlyMixin, TemplateView):
    template_name = "lms/staff/enrollment_invitations.html"

    class InputSerializer(serializers.Serializer):
        branches = serializers.ChoiceField(required=True, choices=())

    def get(self, request, *args, **kwargs):
        site_branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        assert len(site_branches) > 0
        serializer = self.InputSerializer(data=request.GET)
        serializer.fields["branches"].choices = [(b.pk, b.name) for b in site_branches]
        if not serializer.initial_data:
            branch = site_branches[0]
            url = f"{request.path}?branches={branch.pk}"
            return HttpResponseRedirect(url)
        serializer.is_valid(raise_exception=False)
        # Filterset knows how to validate input data too
        invitations = Invitation.objects.select_related("semester").prefetch_related("branches").order_by(
            "-semester__index", "name"
        )
        filter_set = EnrollmentInvitationFilter(
            site_branches, data=self.request.GET, queryset=invitations
        )
        context = self.get_context_data(filter_set, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, filter_set: FilterSet, **kwargs):
        context = {
            "filter_form": filter_set.form,
            "enrollment_invitations": filter_set.qs,
        }
        return context


class InvitationStudentsProgressReportView(CuratorOnlyMixin, View):
    def get(self, request, output_format, invitation_id, *args, **kwargs):
        invitation = get_object_or_404(Invitation.objects.filter(pk=invitation_id))
        report = ProgressReportForInvitation(invitation)
        term = invitation.semester
        file_name = f"sheet_invitation_{invitation.pk}_{term.year}_{term.type}"
        return dataframe_to_response(report.generate(), output_format, file_name)


class AdmissionApplicantsCampaignReportView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, campaign_id, output_format, **kwargs):
        campaign = get_object_or_404(
            Campaign.objects.filter(pk=campaign_id, branch__site_id=settings.SITE_ID)
        )
        report = AdmissionApplicantsCampaignReport(campaign=campaign)
        if output_format == "csv":
            return report.output_csv()
        elif output_format == "xlsx":
            return report.output_xlsx()
        else:
            assert_never(output_format)


class AdmissionApplicantsYearReportView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, year, **kwargs):
        report = AdmissionApplicantsYearReport(year=year)
        if output_format == "csv":
            return report.output_csv()
        elif output_format == "xlsx":
            return report.output_xlsx()
        else:
            assert_never(output_format)


class AdmissionInterviewsReportView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, campaign_id, output_format, **kwargs):
        campaign_queryset = Campaign.objects.filter(
            pk=campaign_id, branch__site_id=settings.SITE_ID
        )
        campaign = get_object_or_404(campaign_queryset)
        report = generate_admission_interviews_report(
            campaign=campaign, url_builder=request.build_absolute_uri
        )
        file_name = f"admission_{campaign.year}_{campaign.branch.code}_interviews"
        return dataframe_to_response(report, output_format, file_name)


class AdmissionExamReportView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, campaign_id, output_format, **kwargs):
        campaign = get_object_or_404(
            Campaign.objects.filter(pk=campaign_id, branch__site_id=settings.SITE_ID)
        )
        report = AdmissionExamReport(campaign=campaign)
        return dataframe_to_response(
            report.generate(), output_format, report.get_filename()
        )


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

    template_name = "lms/staff/student_faces.html"

    class InputSerializer(serializers.Serializer):
        branch = serializers.ChoiceField(required=True, choices=())
        year = serializers.IntegerField(
            label="Year of Admission", required=True, min_value=settings.ESTABLISHED
        )
        type = serializers.ChoiceField(
            required=False, allow_blank=True, choices=StudentTypes.choices
        )

    def get_template_names(self):
        if "print" in self.request.GET:
            self.template_name = "lms/staff/student_faces_printable.html"
        return super().get_template_names()

    def get(self, request, *args, **kwargs):
        site_branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        assert len(site_branches) > 0
        serializer = self.InputSerializer(data=request.GET)
        serializer.fields["branch"].choices = [(b.pk, b.name) for b in site_branches]
        if not serializer.initial_data:
            branch = site_branches[0]
            current_term = get_current_term_pair(branch.get_timezone())
            url = f"{request.path}?branch={branch.pk}&year={current_term.year}&type={StudentTypes.REGULAR}"
            return HttpResponseRedirect(url)
        # Filterset knows how to validate input data but we plan to use this
        # serializer for the future api view
        serializer.is_valid(raise_exception=False)
        filter_set = StudentProfileFilter(
            site_branches, data=self.request.GET, queryset=self.get_queryset()
        )
        context = self.get_context_data(filter_set, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, filter_set: FilterSet, **kwargs):
        context = {
            "filter_form": filter_set.form,
            "student_profiles": filter_set.qs,
            "StudentStatuses": StudentStatuses,
        }
        return context

    def get_queryset(self):
        qs = StudentProfile.objects.select_related("user").order_by(
            "user__last_name", "user__first_name", "pk"
        )
        if "print" in self.request.GET:
            qs = qs.exclude(status__in=StudentStatuses.inactive_statuses)
        return qs


class InterviewerFacesView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/interviewer_faces.html"

    def get_context_data(self, **kwargs):
        context = super(InterviewerFacesView, self).get_context_data(**kwargs)
        users = (
            Interview.interviewers.through.objects.only("user_id")
            .distinct()
            .values_list("user_id", flat=True)
        )
        qs = User.objects.filter(id__in=users.all()).distinct()
        context["students"] = qs
        return context


class CourseParticipantsIntersectionView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/courses_intersection.html"

    def get_context_data(self, **kwargs):
        term_pair = get_current_term_pair()
        all_courses_in_term = Course.objects.filter(
            semester__index=term_pair.index
        ).select_related("meta_course")
        # Get participants
        query_courses = self.request.GET.getlist("course_offerings[]", [])
        query_courses = [int(t) for t in query_courses if t]
        results = list(
            Course.objects.filter(pk__in=query_courses)
            .select_related("meta_course")
            .prefetch_related(
                Prefetch(
                    "enrollment_set",
                    queryset=(
                        Enrollment.active.select_related("student").only(
                            "pk",
                            "course_id",
                            "student_id",
                            "student__username",
                            "student__first_name",
                            "student__last_name",
                            "student__patronymic",
                        )
                    ),
                )
            )
        )
        if len(results) > 1:
            first_course, second_course = (
                {e.student_id for e in co.enrollment_set.all()} for co in results
            )
            intersection = first_course.intersection(second_course)
        else:
            intersection = set()
        context = {
            "course_offerings": all_courses_in_term,
            "intersection": intersection,
            "current_term": "{} {}".format(_(term_pair.type), term_pair.year),
            "results": results,
            "query": {"course_offerings": query_courses},
        }
        return context


def autograde_projects(request):
    if not request.user.is_curator:
        return HttpResponseForbidden()
    try:
        graded = call_command("autograde_projects")
        messages.success(
            request, f"Операция выполнена успешно.<br>" f"Выставлено оценок: {graded}"
        )
    except CommandError as e:
        messages.error(request, str(e))
    return HttpResponseRedirect(reverse("staff:exports"))


def autofail_ungraded(request):
    if not request.user.is_curator:
        return HttpResponseForbidden()
    try:
        graded = call_command("autofail_ungraded", request.site)
        messages.success(
            request, f"Операция выполнена успешно.<br>" f"Выставлено незачетов: {graded}"
        )
    except CommandError as e:
        messages.error(request, str(e))
    return HttpResponseRedirect(reverse("staff:exports"))


# FIXME: replace with staff.api.views.CreateAlumniProfiles (already tested) - needs to write js part
def create_alumni_profiles(request: HttpRequest):
    if not request.user.is_curator:
        return HttpResponseForbidden()

    form = GraduationForm(data=request.POST)
    if form.is_valid():
        graduated_on = form.cleaned_data["graduated_on"]
        create_graduate_profiles(request.site, graduated_on, created_by=request.user)
        messages.success(request, "Операция выполнена успешно")
    else:
        messages.error(request, "Неверный формат даты выпуска")
    return HttpResponseRedirect(reverse("staff:exports"))


def merge_users_view(request: HttpRequest):
    if not request.user.is_curator:
        return HttpResponseForbidden()
    form = MergeUsersForm(data=request.POST)
    if form.is_valid():
        major_user = User.objects.get(email=form.cleaned_data['major_email'])
        minor_user = User.objects.get(email=form.cleaned_data['minor_email'])
        try:
            main_user = merge_users(major=major_user, minor=minor_user)
        except Exception as e:
            messages.error(request, str(e))
        else:
            messages.success(request,
                             mark_safe(f"Пользователи успешно объединены. <a "
                                       f"href={main_user.get_absolute_url()} "
                                       f"target='_blank'>"
                                       f"Ссылка на объединенный профиль</a>"))
    else:
        for field, error_as_list in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            label = "Общее" if label == "__all__" else label
            errors = "<br>".join(str(error) for error in error_as_list)
            messages.error(request, mark_safe(f"{label}:<br>{errors}"))
    return HttpResponseRedirect(reverse("staff:exports"))


def badge_number_from_csv_view(request: HttpRequest):
    if not request.user.is_curator:
        return HttpResponseForbidden()
    form = BadgeNumberFromCSVForm(data=request.POST)
    if form.is_valid():
        csv_file = form.cleaned_data['csv_file']
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            number_done = badge_number_from_csv(decoded_file)
        except Exception as e:
            messages.error(request, _(f"File read error: {str(e)}"))
        else:
            messages.success(request, f"Номера пропусков успешно выставлены. Обработано {number_done} пользователей")
    else:
        for field, error_as_list in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            label = "Общее" if label == "__all__" else label
            errors = "<br>".join(str(error) for error in error_as_list)
            messages.error(request, mark_safe(f"{label}:<br>{errors}"))
    return HttpResponseRedirect(reverse("staff:exports"))


class SurveySubmissionsReportView(CuratorOnlyMixin, generic.base.View):
    FORMATS = ("csv", "xlsx")

    def get(self, request, survey_pk, output_format, *args, **kwargs):
        if output_format not in self.FORMATS:
            return HttpResponseBadRequest(f"Supported formats {self.FORMATS}")
        query = CourseSurvey.objects.filter(pk=survey_pk).select_related(
            "form", "course", "course__meta_course", "course__semester"
        )
        survey = get_object_or_404(query)
        report = SurveySubmissionsReport(survey)
        return getattr(report, f"output_{output_format}")()


class SurveySubmissionsStatsView(CuratorOnlyMixin, TemplateView):
    template_name = "staff/survey_submissions_stats.html"

    def get_context_data(self, **kwargs):
        survey_pk = self.kwargs["survey_pk"]
        query = CourseSurvey.objects.filter(pk=survey_pk).select_related(
            "form", "course", "course__meta_course", "course__semester"
        )
        survey = get_object_or_404(query)
        report = SurveySubmissionsStats(survey)
        stats = report.calculate()
        return {
            "survey": survey,
            "total_submissions": stats["total_submissions"],
            "data": stats["fields"],
        }


class GradeBookListView(CuratorOnlyMixin, GradeBookListBaseView):
    template_name = "staff/gradebook_list.html"

    def get_term_threshold(self):
        latest_term = Semester.objects.order_by("-index").first()
        return latest_term.index

    def get_context_data(self, **kwargs):
        semester_list = list(self.object_list)
        # Add stub term if we have only 1 term for the ongoing academic year
        if semester_list:
            current = semester_list[0]
            if current.type == SemesterTypes.AUTUMN:
                next_term = current.term_pair.get_next()
                term = Semester(type=next_term.type, year=next_term.year)
                term.course_offerings = []
                semester_list.insert(0, term)
            semester_list = [(a, s) for s, a in core.utils.chunks(semester_list, 2)]
            for academic_year in semester_list:
                # Group by main branch name
                for term in academic_year:
                    courses = bucketize(
                        term.course_offerings, key=lambda c: c.main_branch.name
                    )
                    term.course_offerings = courses
        context = {
            'CourseDurations': CourseDurations,
            "semester_list": semester_list
        }
        return context


class OfficialDiplomasListView(CuratorOnlyMixin, TemplateView):
    template_name = "staff/official_diplomas_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        year = int(self.kwargs["year"])
        month = int(self.kwargs["month"])
        day = int(self.kwargs["day"])
        date = datetime.date(year, month, day)
        graduate_profiles = get_list_or_404(
            GraduateProfile.objects.for_site(self.request.site)
            .with_official_diploma()
            .filter(diploma_issued_on=date)
            .select_related("student_profile__user")
            .only("student_profile__user")
            .order_by(
                "student_profile__user__last_name",
                "student_profile__user__first_name",
                "student_profile__user__patronymic",
            )
        )
        graduated_users = [g.student_profile.user for g in graduate_profiles]
        graduates_data = [
            (g.get_absolute_url(), g.get_full_name(last_name_first=True))
            for g in graduated_users
        ]
        context.update({"date": date, "graduates_data": graduates_data})
        return context


class OfficialDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, year, month, day, *args, **kwargs):
        diploma_issued_on = datetime.date(int(year), int(month), int(day))
        report = OfficialDiplomasReport(diploma_issued_on)
        site_aware_queryset = report.get_queryset().filter(
            branch__site=self.request.site
        )
        if not site_aware_queryset.count():
            raise Http404
        df = report.generate(site_aware_queryset)
        date_issued = diploma_issued_on.isoformat().replace("-", "_")
        file_name = "official_diplomas_{}".format(date_issued)
        return dataframe_to_response(df, "csv", file_name)


class OfficialDiplomasTeXView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/official_diplomas.html"

    def get_context_data(self, year, month, day, **kwargs):
        diploma_issued_on = datetime.date(int(year), int(month), int(day))
        report = OfficialDiplomasReport(diploma_issued_on)
        student_profiles = report.get_queryset().filter(branch__site=self.request.site)
        students = (sp.user for sp in student_profiles)
        courses_qs = report.get_courses_queryset(students).annotate(
            classes_total=Count("courseclass")
        )
        courses = {c.pk: c for c in courses_qs}

        diploma_student_profiles = [
            generate_tex_student_profile_for_diplomas(sp, courses, is_official=True)
            for sp in student_profiles
        ]

        context = {
            "diploma_issued_on": diploma_issued_on,
            "students": diploma_student_profiles,
        }
        return context


class StudentAcademicDisciplineLogListView(CuratorOnlyMixin, FilterView):
    model = StudentAcademicDisciplineLog
    context_object_name = 'logs'
    filterset_class = StudentAcademicDisciplineLogFilter
    template_name = 'lms/staff/academic_discipline_log.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = context['filter'].form
        paginator_url = reverse("staff:academic_discipline_log_list")
        query_params = self.request.GET.copy()
        if "page" in query_params:
            query_params.pop("page")
        context['paginator_url'] = paginator_url + "?" + query_params.urlencode()
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get("download_csv"):
            return self.download_csv(request)
        elif request.GET.get("mark_processed"):
            return self.mark_processed(request)
        return super().dispatch(request, *args, **kwargs)

    def download_csv(self, request):
        filterset = self.filterset_class(data=request.GET, queryset=self.get_queryset())
        filtered_qs = filterset.qs

        today = formats.date_format(datetime.datetime.now(), "SHORT_DATE_FORMAT")
        filename = f"academic_discipline_logs_{today}.csv"

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['ФИО', "Ссылка на ЛК", _("Branch"), _("Type"), _("Telegram"), _('email address'),
                         _('Former field of study'), _('Field of study')])

        for log in filtered_qs:
            student_profile = log.student_profile
            user = student_profile.user
            writer.writerow([
                student_profile.get_full_name(),
                request.build_absolute_uri(student_profile.get_absolute_url()),
                student_profile.branch.name,
                student_profile.get_type_display(),
                user.telegram_username,
                user.email,
                log.former_academic_discipline,
                log.academic_discipline
            ])

        return response

    def mark_processed(self, request):
        filterset = self.filterset_class(data=request.GET, queryset=self.get_queryset())
        filtered_qs = filterset.qs.filter(is_processed=False)
        filtered_qs.update(is_processed=True, processed_at=timezone.now().date())

        query_params = request.GET.copy()
        query_params.pop("mark_processed")
        return HttpResponseRedirect(reverse('staff:academic_discipline_log_list') + "?" + query_params.urlencode())


class StudentStatusLogListView(CuratorOnlyMixin, FilterView):
    model = StudentStatusLog
    context_object_name = 'logs'
    filterset_class = StudentStatusLogFilter
    template_name = 'lms/staff/status_log.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = context['filter'].form
        paginator_url = reverse("staff:status_log_list")
        query_params = self.request.GET.copy()
        if "page" in query_params:
            query_params.pop("page")
        context['paginator_url'] = paginator_url + "?" + query_params.urlencode()
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get("download_csv"):
            return self.download_csv(request)
        elif request.GET.get("mark_processed"):
            return self.mark_processed(request)
        return super().dispatch(request, *args, **kwargs)

    def download_csv(self, request):
        filterset = self.filterset_class(data=request.GET, queryset=self.get_queryset())
        filtered_qs = filterset.qs

        today = formats.date_format(datetime.datetime.now(), "SHORT_DATE_FORMAT")
        filename = f"status_logs_{today}.csv"

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['ФИО', "Ссылка на ЛК", _("Branch"), _("Type"), _("Telegram"), _('email address'),
                         _('Former status'), _('Status')])

        for log in filtered_qs:
            student_profile = log.student_profile
            user = student_profile.user
            writer.writerow([
                student_profile.get_full_name(),
                request.build_absolute_uri(student_profile.get_absolute_url()),
                student_profile.branch.name,
                student_profile.get_type_display(),
                user.telegram_username,
                user.email,
                log.get_former_status_display(),
                log.get_status_display()
            ])

        return response

    def mark_processed(self, request):
        filterset = self.filterset_class(data=request.GET, queryset=self.get_queryset())
        filtered_qs = filterset.qs.filter(is_processed=False)
        filtered_qs.update(is_processed=True, processed_at=timezone.now().date())

        query_params = request.GET.copy()
        query_params.pop("mark_processed")
        return HttpResponseRedirect(reverse('staff:status_log_list') + "?" + query_params.urlencode())
