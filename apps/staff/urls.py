from django.urls import include, path, re_path, register_converter

from courses.urls import RE_COURSE_URI
from learning.gradebook.views import (
    GradeBookCSVView, GradeBookView, ImportAssignmentScoresByEnrollmentIDView,
    ImportAssignmentScoresByStepikIDView, ImportAssignmentScoresByYandexLoginView,
    ImportCourseGradesByEnrollmentIDView, ImportCourseGradesByYandexLoginView, ImportCourseGradesByStepikIDView
)
from staff.api.views import CreateAlumniProfiles, StudentSearchJSONView
from staff.views.views import (
    AdmissionApplicantsCampaignReportView, AdmissionExamReportView,
    AdmissionInterviewsReportView, CourseParticipantsIntersectionView,
    EnrollmentInvitationListView, ExportsView, FutureGraduateDiplomasCSVView,
    FutureGraduateDiplomasTeXView, FutureGraduateStatsView, GradeBookListView,
    HintListView, InterviewerFacesView, InvitationStudentsProgressReportView,
    OfficialDiplomasCSVView, OfficialDiplomasListView, OfficialDiplomasTeXView,
    ProgressReportForSemesterView, ProgressReportFullView, StudentFacesView,
    StudentSearchCSVView, StudentSearchView, SurveySubmissionsReportView,
    SurveySubmissionsStatsView, WillGraduateStatsReportView, AdmissionApplicantsYearReportView,
    StudentAcademicDisciplineLogListView, StudentStatusLogListView, badge_number_from_csv_view, merge_users_view
)
from staff.views.send_letters_view import SendLettersView
from staff.views.views import autograde_projects, autofail_ungraded, create_alumni_profiles
from staff.views.enrolees_selection import EnroleesSelectionCSVView, EnroleesSelectionListView

app_name = 'staff'


class SupportedExportFormatConverter:
    regex = 'csv|xlsx'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(SupportedExportFormatConverter, 'export_fmt')


urlpatterns = [
    path('gradebooks/', include([
        path('', GradeBookListView.as_view(), name='gradebook_list'),
        re_path(RE_COURSE_URI, include([
            path('', GradeBookView.as_view(is_for_staff=True, permission_required="teaching.view_gradebook"), name='gradebook'),
            path('csv/', GradeBookCSVView.as_view(permission_required="teaching.view_gradebook"), name='gradebook_csv'),
        ])),
        path('<int:course_id>/import/', include([
            path('assignments-stepik', ImportAssignmentScoresByStepikIDView.as_view(), name='gradebook_import_scores_by_stepik_id'),
            path('assignments-yandex', ImportAssignmentScoresByYandexLoginView.as_view(), name='gradebook_import_scores_by_yandex_login'),
            path('assignments-enrollments', ImportAssignmentScoresByEnrollmentIDView.as_view(), name='gradebook_import_scores_by_enrollment_id'),
            path('course-grades-stepik', ImportCourseGradesByStepikIDView.as_view(), name='gradebook_import_course_grades_by_stepik_id'),
            path('course-grades-yandex', ImportCourseGradesByYandexLoginView.as_view(), name='gradebook_import_course_grades_by_yandex_login'),
            path('course-grades-enrollments', ImportCourseGradesByEnrollmentIDView.as_view(), name='gradebook_import_course_grades_by_enrollment_id')
        ])),
    ])),

    path('student-search/', StudentSearchView.as_view(), name='student_search'),
    path('student-search.json', StudentSearchJSONView.as_view(), name='student_search_json'),
    # Note: CSV view doesn't use pagination
    path('student-search.csv', StudentSearchCSVView.as_view(), name='student_search_csv'),


    path('faces/', StudentFacesView.as_view(), name='student_faces'),
    path('faces/interviewers/', InterviewerFacesView.as_view(), name='interviewer_faces'),

    path('commands/create-alumni-profiles/', create_alumni_profiles, name='create_alumni_profiles'),  # deprecated
    path('commands/autograde-projects/', autograde_projects, name='autograde_projects'),
    path('commands/autofail_ungraded/', autofail_ungraded, name='autofail_ungraded'),
    path('commands/merge_users/', merge_users_view, name='merge_users'),
    path('commands/badge_number_from_csv/', badge_number_from_csv_view, name='badge_number_from_csv'),
    path('commands/send_letters/', SendLettersView.as_view(), name='send_letters'),
    

    path('course-participants/', CourseParticipantsIntersectionView.as_view(), name='course_participants_intersection'),


    path('exports/', ExportsView.as_view(), name='exports'),

    re_path(r'^reports/learning/will_graduate/(?P<output_format>csv|xlsx)/$', WillGraduateStatsReportView.as_view(), name='exports_report_will_graduate'),
    re_path(r'^reports/future-graduates/(?P<branch_id>\d+)/', include([
        path('stats/', FutureGraduateStatsView.as_view(), name='export_future_graduates_stats'),
        path('tex/', FutureGraduateDiplomasTeXView.as_view(), name='exports_future_graduates_diplomas_tex'),
        path('csv/', FutureGraduateDiplomasCSVView.as_view(), name='exports_future_graduates_diplomas_csv'),
    ])),
    path('reports/enrollment-invitations/', include([
        path('', EnrollmentInvitationListView.as_view(), name='enrollment_invitations_list'),
        re_path(r'^(?P<invitation_id>\d+)/(?P<output_format>csv|xlsx)/$', InvitationStudentsProgressReportView.as_view(), name='students_progress_report_for_invitation'),
    ])),
    path('reports/academic_discipline_logs/', include([
        path('', StudentAcademicDisciplineLogListView.as_view(), name='academic_discipline_log_list')
    ])),
    path('reports/status_logs/', include([
        path('', StudentStatusLogListView.as_view(), name='status_log_list')
    ])),
    path('reports/students-progress/', include([
        re_path(r'^(?P<output_format>csv|xlsx)/(?P<on_duplicate>max|last)/$', ProgressReportFullView.as_view(), name='students_progress_report'),
        re_path(r'^terms/(?P<term_year>\d+)/(?P<term_type>\w+)/(?P<output_format>csv|xlsx)/$', ProgressReportForSemesterView.as_view(), name='students_progress_report_for_term'),
    ])),
    re_path(r'^reports/official-diplomas/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/', include([
        path('list/', OfficialDiplomasListView.as_view(), name='exports_official_diplomas_list'),
        path('tex/', OfficialDiplomasTeXView.as_view(), name='exports_official_diplomas_tex'),
        path('csv/', OfficialDiplomasCSVView.as_view(), name='exports_official_diplomas_csv'),
    ])),
    path('reports/admission/<int:campaign_id>/campain_applicants/<export_fmt:output_format>/',
         AdmissionApplicantsCampaignReportView.as_view(), name='exports_report_admission_campaign_applicants'),
    path('reports/admission/<int:year>/year_applicants/<export_fmt:output_format>/',
         AdmissionApplicantsYearReportView.as_view(), name='exports_report_admission_year_applicants'),
    path('reports/admission/<int:campaign_id>/interviews/<export_fmt:output_format>/', AdmissionInterviewsReportView.as_view(), name='exports_report_admission_interviews'),
    path('reports/admission/<int:campaign_id>/exam/<export_fmt:output_format>/', AdmissionExamReportView.as_view(), name='exports_report_admission_exam'),
    re_path(r'^reports/surveys/(?P<survey_pk>\d+)/(?P<output_format>csv|xlsx)/$', SurveySubmissionsReportView.as_view(), name='exports_report_survey_submissions'),
    re_path(r'^reports/surveys/(?P<survey_pk>\d+)/txt/$', SurveySubmissionsStatsView.as_view(), name='exports_report_survey_submissions_stats'),


    path('warehouse/', HintListView.as_view(), name='staff_warehouse'),

    path('api/staff/', include(([
        path('alumni-profiles/', CreateAlumniProfiles.as_view(), name='create_alumni_profiles'),
    ], 'api'))),
    path('enrolees-selection/', include([
        path('', EnroleesSelectionListView.as_view(), name='enrolees_selection_list'),
        re_path(RE_COURSE_URI, include([
            path('csv/', EnroleesSelectionCSVView.as_view(), name='enrolees_selection_csv'),
        ]))
    ])),
]
