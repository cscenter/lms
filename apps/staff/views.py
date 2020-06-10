# -*- coding: utf-8 -*-
import datetime
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.core.management import CommandError
from django.core.management import call_command
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, get_list_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic, View
from django_filters.views import BaseFilterView
from vanilla import TemplateView

import core.utils
from admission.models import Campaign, Interview
from admission.reports import AdmissionApplicantsReport, AdmissionExamReport
from core.models import Branch
from core.urls import reverse
from courses.constants import SemesterTypes
from courses.models import Course, Semester
from courses.utils import get_current_term_pair, get_term_index
from learning.gradebook.views import GradeBookListBaseView
from learning.models import Enrollment, Invitation, GraduateProfile
from learning.reports import FutureGraduateDiplomasReport, ProgressReportFull, \
    ProgressReportForSemester, WillGraduateStatsReport, \
    ProgressReportForInvitation, dataframe_to_response, OfficialDiplomasReport
from learning.settings import AcademicDegreeLevels, StudentStatuses, \
    GradeTypes
from staff.forms import GraduationForm
from staff.models import Hint
from staff.serializers import FacesQueryParams
from staff.tex import generate_student_profiles_for_tex_diplomas
from surveys.models import CourseSurvey
from surveys.reports import SurveySubmissionsReport, SurveySubmissionsStats
from users.filters import StudentFilter
from users.mixins import CuratorOnlyMixin
from users.models import User, StudentProfile, StudentTypes
from users.services import get_student_progress, create_graduate_profiles, \
    get_graduate_profile


class StudentSearchCSVView(CuratorOnlyMixin, BaseFilterView):
    context_object_name = 'applicants'
    model = StudentProfile
    filterset_class = StudentFilter

    def get_queryset(self):
        return (StudentProfile.objects
                .select_related('user', 'branch', 'graduate_profile'))

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)

        if not self.filterset.is_bound or self.filterset.is_valid() or not self.get_strict():
            queryset = self.filterset.qs
        else:
            queryset = self.filterset.queryset.none()
        report = ProgressReportFull(grade_getter="grade_honest")
        custom_qs = report.get_queryset(base_queryset=queryset)
        df = report.generate(queryset=custom_qs)
        return dataframe_to_response(df, 'csv', report.get_filename())


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
            'curriculum_years': (StudentProfile.objects
                                 .values_list('year_of_curriculum',
                                              flat=True)
                                 .filter(year_of_curriculum__isnull=False)
                                 .order_by('year_of_curriculum')
                                 .distinct()),
            "types": StudentTypes.choices,
            "status": StudentStatuses.values,
            "cnt_enrollments": range(StudentFilter.ENROLLMENTS_MAX + 1)
        }
        return context


class ExportsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/exports.html"

    def get_context_data(self, **kwargs):
        current_term = get_current_term_pair()
        prev_term = current_term.get_prev()
        graduation_form = GraduationForm()
        graduation_form.helper.form_action = reverse('staff:create_alumni_profiles')
        invitations = core.utils.bucketize(Invitation.objects
                                           .select_related('branch')
                                           .order_by('branch', 'name'),
                                           key=lambda i: i.branch)
        official_diplomas_dates = (GraduateProfile.objects
                                   .for_site(self.request.site)
                                   .with_official_diploma()
                                   .distinct('diploma_issued_on')
                                   .order_by('-diploma_issued_on')
                                   .values_list('diploma_issued_on', flat=True))
        context = {
            "alumni_profiles_form": graduation_form,
            "current_term": current_term,
            "prev_term": {"year": prev_term.year, "type": prev_term.type},
            "campaigns": (Campaign.objects
                          .select_related("branch")
                          .order_by("-year", "branch__name")),
            "invitations": invitations,
            "branches": Branch.objects.filter(site_id=settings.SITE_ID),
            "official_diplomas_dates": official_diplomas_dates,
        }
        return context


class FutureGraduateStatsView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas_stats.html"
    BAD_GRADES = [GradeTypes.UNSATISFACTORY, GradeTypes.NOT_GRADED]

    def get_context_data(self, branch_id, **kwargs):
        student_profiles = (StudentProfile.objects
                            .filter(type=StudentTypes.REGULAR,
                                    branch_id=branch_id,
                                    status=StudentStatuses.WILL_GRADUATE)
                            .select_related('user')
                            .order_by('user__last_name', 'user__first_name',
                                      'user_id'))
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
            enrollments = progress[s.id].get('enrollments', [])
            projects = progress[s.id].get('projects', [])
            shad = progress[s.id].get('shad', [])
            graduate_profile = get_graduate_profile(student_profile)
            if graduate_profile and len(graduate_profile.academic_disciplines.all()) >= 2:
                finished_two_or_more_programs.add(s)
            by_year_of_admission[student_profile.year_of_admission].add(student_profile)
            degree_year = AcademicDegreeLevels.BACHELOR_SPECIALITY_1
            if student_profile.level_of_education_on_admission == degree_year:
                enrolled_on_first_course.add(s)
            # Count most_courses_students
            s.passed_courses = sum(1 for e in enrollments if e.grade not in self.BAD_GRADES)
            s.passed_courses += sum(1 for c in shad if c.grade not in self.BAD_GRADES)
            if not most_courses_students:
                most_courses_students = {s}
            else:
                most_courses_student = next(iter(most_courses_students))
                if s.passed_courses == most_courses_student.passed_courses:
                    most_courses_students.add(s)
                elif s.passed_courses > most_courses_student.passed_courses:
                    most_courses_students = {s}
            s.pass_open_courses = sum(e.course.is_club_course for e in enrollments
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
            enrollment_term_index = get_term_index(
                student_profile.year_of_admission,
                SemesterTypes.AUTUMN)
            for ps in projects:
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
                if enrollment.grade == GradeTypes.EXCELLENT:
                    excellent_total += 1
                elif enrollment.grade == GradeTypes.GOOD:
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
            'by_enrollment_year': dict(by_year_of_admission),
            'enrolled_on_first_course': enrolled_on_first_course,
            'most_courses_students': most_courses_students,
            'most_courses_in_term_students': most_courses_in_term_students,
            'most_open_courses_students': most_open_courses_students,
            'student_profiles': student_profiles,
            "unique_teachers_count": len(unique_teachers),
            "total_hours": int(total_hours),
            "unique_courses": unique_courses, "good_total": good_total,
            "excellent_total": excellent_total,
            "total_passed_courses": total_passed_courses,
            "unique_projects": unique_projects
        }
        return context


class FutureGraduateDiplomasTeXView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/diplomas.html"

    def get_context_data(self, branch_id, **kwargs):
        branch = Branch.objects.get(pk=branch_id)
        report = FutureGraduateDiplomasReport(branch)
        student_profiles = generate_student_profiles_for_tex_diplomas(report)

        context = {
            "branch": branch,
            "is_official": False,
            "student_profiles": student_profiles
        }
        return context


class FutureGraduateDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, branch_id, *args, **kwargs):
        branch = get_object_or_404(Branch.objects.filter(pk=branch_id))
        report = FutureGraduateDiplomasReport(branch)
        df = report.generate()
        return dataframe_to_response(df, 'csv', report.get_filename())


class ProgressReportFullView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, *args, **kwargs):
        report = ProgressReportFull(grade_getter="grade_honest")
        filename = report.get_filename()
        return dataframe_to_response(report.generate(), output_format, filename)


class ProgressReportForSemesterView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, output_format, *args, **kwargs):
        # Validate year and term GET params
        try:
            term_year = int(self.kwargs['term_year'])
            if term_year < settings.FOUNDATION_YEAR:
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
        return dataframe_to_response(report.generate(), output_format, filename)


class InvitationStudentsProgressReportView(CuratorOnlyMixin, View):
    def get(self, request, output_format, invitation_id, *args, **kwargs):
        invitation = get_object_or_404(Invitation.objects
                                       .filter(pk=invitation_id))
        report = ProgressReportForInvitation(invitation)
        return dataframe_to_response(report.generate(), output_format,
                                     report.get_filename())


class AdmissionApplicantsReportView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, campaign_id, output_format, **kwargs):
        campaign = get_object_or_404(Campaign.objects.filter(pk=campaign_id))
        report = AdmissionApplicantsReport(campaign=campaign)
        if output_format == "csv":
            return report.output_csv()
        elif output_format == "xlsx":
            return report.output_xlsx()


class AdmissionExamReportView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, campaign_id, output_format, **kwargs):
        campaign = get_object_or_404(Campaign.objects.filter(pk=campaign_id))
        report = AdmissionExamReport(campaign=campaign)
        return dataframe_to_response(report.generate(), output_format,
                                     report.get_filename())


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
        context = self.get_context_data(query_params, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, query_params, **kwargs):
        branch_code = query_params.validated_data.get('branch',
                                                      settings.DEFAULT_BRANCH_CODE)
        branch = get_object_or_404(Branch.objects
                                   .filter(code=branch_code,
                                           site_id=settings.SITE_ID))
        year_of_admission = query_params.validated_data.get('year')
        if not year_of_admission:
            year_of_admission = get_current_term_pair(
                branch.get_timezone()).year
        current_year = get_current_term_pair(branch.get_timezone()).year
        context = {
            'students': self.get_queryset(branch, year_of_admission),
            "years": reversed(range(branch.established, current_year + 1)),
            "current_year": year_of_admission,
            "current_branch": branch,
            "branches": Branch.objects.for_site(site_id=settings.SITE_ID)
        }
        return context

    def get_template_names(self):
        if "print" in self.request.GET:
            self.template_name = "staff/student_faces_printable.html"
        return super(StudentFacesView, self).get_template_names()

    def get_queryset(self, branch, year_of_admission):
        qs = (User.objects
              .filter(student_profiles__branch=branch,
                      student_profiles__year_of_admission=year_of_admission)
              .distinct('last_name', 'first_name', 'pk')
              .order_by('last_name', 'first_name', 'pk')
              .prefetch_related("groups"))
        if "print" in self.request.GET:
            qs = qs.exclude(status__in=StudentStatuses.inactive_statuses)
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
        term_pair = get_current_term_pair()
        all_courses_in_term = (Course.objects
                               .filter(semester__index=term_pair.index)
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
            'current_term': "{} {}".format(_(term_pair.type), term_pair.year),
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
        create_graduate_profiles(request.site, graduated_on)
        messages.success(request, f"Операция выполнена успешно.")
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


class OfficialDiplomasListView(CuratorOnlyMixin, TemplateView):
    template_name = 'staff/official_diplomas_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        year = int(self.kwargs['year'])
        month = int(self.kwargs['month'])
        day = int(self.kwargs['day'])
        date = datetime.date(year, month, day)
        graduate_profiles = get_list_or_404(GraduateProfile.objects
                                            .for_site(self.request.site)
                                            .with_official_diploma()
                                            .filter(diploma_issued_on=date)
                                            .select_related('student_profile__user')
                                            .only('student_profile__user')
                                            .order_by('student_profile__user__last_name',
                                                      'student_profile__user__first_name',
                                                      'student_profile__user__patronymic'))
        graduated_users = [g.student_profile.user for g in graduate_profiles]
        graduates_data = [(g.get_absolute_url(), g.get_full_name(last_name_first=True))
                          for g in graduated_users]
        context.update({
            'date': date,
            'graduates_data': graduates_data
        })
        return context


class OfficialDiplomasCSVView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, year, month, day, *args, **kwargs):
        diploma_issued_on = datetime.date(int(year), int(month), int(day))
        report = OfficialDiplomasReport(diploma_issued_on)
        site_aware_queryset = report.get_queryset().filter(branch__site=self.request.site)
        if not site_aware_queryset.count():
            raise Http404
        df = report.generate(site_aware_queryset)
        return dataframe_to_response(df, 'csv', report.get_filename())


class OfficialDiplomasTeXView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "staff/official_diplomas.html"

    def get_context_data(self, year, month, day, **kwargs):
        diploma_issued_on = datetime.date(int(year), int(month), int(day))
        report = OfficialDiplomasReport(diploma_issued_on)
        # TODO: pass site aware queryset to TeX generator
        student_profiles = generate_student_profiles_for_tex_diplomas(report)

        context = {
            "diploma_issued_on": diploma_issued_on,
            "is_official": True,
            "student_profiles": student_profiles
        }
        return context
