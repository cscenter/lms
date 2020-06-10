from django.conf.urls import include, url
from django.urls import path, re_path, register_converter

from courses.urls import RE_COURSE_URI
from learning.gradebook.views import GradeBookView, GradeBookCSVView, \
    AssignmentScoresImportByStepikIDView, \
    AssignmentScoresImportByYandexLoginView
from staff.views import HintListView, StudentSearchView, ExportsView, \
    FutureGraduateStatsView, FutureGraduateDiplomasTeXView, \
    FutureGraduateDiplomasCSVView, ProgressReportFullView, \
    OfficialDiplomasListView, OfficialDiplomasCSVView, OfficialDiplomasTeXView, \
    ProgressReportForSemesterView, AdmissionApplicantsReportView, \
    StudentFacesView, InterviewerFacesView, autograde_projects, \
    CourseParticipantsIntersectionView, WillGraduateStatsReportView, \
    SurveySubmissionsReportView, \
    SurveySubmissionsStatsView, GradeBookListView, create_alumni_profiles, \
    InvitationStudentsProgressReportView, StudentSearchCSVView, \
    AdmissionExamReportView
from staff.api.views import StudentSearchJSONView

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
        path('<int:course_id>/import/stepic', AssignmentScoresImportByStepikIDView.as_view(is_for_staff=True), name='gradebook_csv_import_stepic'),
        path('<int:course_id>/import/yandex', AssignmentScoresImportByYandexLoginView.as_view(is_for_staff=True), name='gradebook_csv_import_yandex'),
    ])),

    path('student-search/', StudentSearchView.as_view(), name='student_search'),
    path('student-search.json', StudentSearchJSONView.as_view(), name='student_search_json'),
    # Note: CSV view doesn't use pagination
    path('student-search.csv', StudentSearchCSVView.as_view(), name='student_search_csv'),


    path('faces/', StudentFacesView.as_view(), name='student_faces'),
    path('faces/interviewers/', InterviewerFacesView.as_view(), name='interviewer_faces'),

    path('commands/create-alumni-profiles/', create_alumni_profiles, name='create_alumni_profiles'),
    path('commands/autograde-projects/', autograde_projects, name='autograde_projects'),

    path('course-participants/', CourseParticipantsIntersectionView.as_view(), name='course_participants_intersection'),


    path('exports/', ExportsView.as_view(), name='exports'),

    # FIXME: Is it useful?
    url(r'^reports/learning/will_graduate/(?P<output_format>csv|xlsx)/$', WillGraduateStatsReportView.as_view(), name='exports_report_will_graduate'),
    url(r'^reports/future-graduates/(?P<branch_id>\d+)/', include([
        url(r'^stats/$', FutureGraduateStatsView.as_view(), name='export_future_graduates_stats'),
        url(r'^tex/$', FutureGraduateDiplomasTeXView.as_view(), name='exports_future_graduates_diplomas_tex'),
        url(r'^csv/$', FutureGraduateDiplomasCSVView.as_view(), name='exports_future_graduates_diplomas_csv'),
    ])),
    url(r'^reports/students-progress/', include([
        url(r'^(?P<output_format>csv|xlsx)/$', ProgressReportFullView.as_view(), name='students_progress_report'),
        url(r'^terms/(?P<term_year>\d+)/(?P<term_type>\w+)/(?P<output_format>csv|xlsx)/$', ProgressReportForSemesterView.as_view(), name='students_progress_report_for_term'),
        url(r'^invitations/(?P<invitation_id>\d+)/(?P<output_format>csv|xlsx)/$', InvitationStudentsProgressReportView.as_view(), name='students_progress_report_for_invitation'),
    ])),
    url(r'^reports/official-diplomas/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/', include([
        url(r'^list/$', OfficialDiplomasListView.as_view(), name='exports_official_diplomas_list'),
        url(r'^tex/$', OfficialDiplomasTeXView.as_view(), name='exports_official_diplomas_tex'),
        url(r'^csv/$', OfficialDiplomasCSVView.as_view(), name='exports_official_diplomas_csv'),
    ])),
    path('reports/admission/<int:campaign_id>/applicants/<export_fmt:output_format>/', AdmissionApplicantsReportView.as_view(), name='exports_report_admission_applicants'),
    path('reports/admission/<int:campaign_id>/exam/<export_fmt:output_format>/', AdmissionExamReportView.as_view(), name='exports_report_admission_exam'),
    url(r'^reports/surveys/(?P<survey_pk>\d+)/(?P<output_format>csv|xlsx)/$', SurveySubmissionsReportView.as_view(), name='exports_report_survey_submissions'),
    url(r'^reports/surveys/(?P<survey_pk>\d+)/txt/$', SurveySubmissionsStatsView.as_view(), name='exports_report_survey_submissions_stats'),


    path('warehouse/', HintListView.as_view(), name='staff_warehouse'),
]


