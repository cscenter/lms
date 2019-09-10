from django.conf.urls import include, url
from django.urls import path, re_path

from courses.urls import RE_COURSE_URI
from learning.gradebook.views import GradeBookView, GradeBookCSVView
from staff.views import HintListView, StudentSearchView, StudentSearchJSONView, \
    ExportsView, StudentsDiplomasStatsView, StudentsDiplomasTexView, \
    StudentsDiplomasCSVView, ProgressReportFullView, \
    ProgressReportForSemesterView, AdmissionReportView, \
    StudentFacesView, InterviewerFacesView, autograde_projects, \
    CourseParticipantsIntersectionView, WillGraduateStatsReportView, \
    SurveySubmissionsReportView, \
    SurveySubmissionsStatsView, GradeBookListView, create_alumni_profiles

app_name = 'staff'

urlpatterns = [
    url(r'^warehouse/$', HintListView.as_view(), name='staff_warehouse'),
    url(r'^course-marks/', include([
        path('', GradeBookListView.as_view(), name='gradebook_list'),
        re_path(RE_COURSE_URI, include([
            path('', GradeBookView.as_view(is_for_staff=True, permission_required="teaching.view_gradebook"), name='gradebook'),
            path('csv/', GradeBookCSVView.as_view(permission_required="teaching.view_gradebook"), name='gradebook_csv'),
        ])),
    ])),
    url(r'^student-search/$',
        StudentSearchView.as_view(),
        name='student_search'),
    url(r'^faces/interviewers/$',
        InterviewerFacesView.as_view(),
        name='interviewer_faces'),
    url(r'^faces/$', StudentFacesView.as_view(), name='student_faces'),
    path('commands/create_alumni_profiles/', create_alumni_profiles, name='create_alumni_profiles'),
    url(r'^projects/autograde/$',
        autograde_projects,
        name='autograde_projects'),
    url(r'^course-participants/$',
        CourseParticipantsIntersectionView.as_view(),
        name='course_participants_intersection'),
    url(r'^student-search.json$',
        StudentSearchJSONView.as_view(),
        name='student_search_json'),

    url(r'^exports/', include([
        url(r'^$', ExportsView.as_view(), name='exports'),
        url(r'^alumni/(?P<branch_id>\d+)/', include([
            url(r'^stats/$', StudentsDiplomasStatsView.as_view(), name='exports_alumni_stats'),
            url(r'^tex/$', StudentsDiplomasTexView.as_view(), name='exports_students_diplomas_tex'),
            url(r'^csv/$', StudentsDiplomasCSVView.as_view(), name='exports_students_diplomas_csv'),
        ])),
        url(r'^sheet/csv/$',
            ProgressReportFullView.as_view(output_format="csv"),
            name='exports_sheet_all_students_csv'),
        url(r'^reports/learning/will_graduate/(?P<output_format>csv|xlsx)/$',
            WillGraduateStatsReportView.as_view(),
            name='exports_report_will_graduate'),
        path('reports/admission/<int:campaign_id>/<str:output_format>/',
             AdmissionReportView.as_view(),
             name='exports_report_admission'),
        url(r'^reports/surveys/(?P<survey_pk>\d+)/(?P<output_format>csv|xlsx)/$',
            SurveySubmissionsReportView.as_view(),
            name='exports_report_survey_submissions'),
        url(r'^reports/surveys/(?P<survey_pk>\d+)/txt/$',
            SurveySubmissionsStatsView.as_view(),
            name='exports_report_survey_submissions_stats'),
        url(r'^sheet/xlsx/$',
            ProgressReportFullView.as_view(output_format="xlsx"),
            name='exports_sheet_all_students_xlsx'),

        url(r'^sheet/(?P<term_year>\d+)/(?P<term_type>\w+)/csv/$',
            ProgressReportForSemesterView.as_view(output_format="csv"),
            name='exports_students_sheet_filter_by_semester_csv'),
        url(r'^sheet/(?P<term_year>\d+)/(?P<term_type>\w+)/xlsx/$',
            ProgressReportForSemesterView.as_view(output_format="xlsx"),
            name='exports_students_sheet_filter_by_semester_xlsx'),
    ])),
]


