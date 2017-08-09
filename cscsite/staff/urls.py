from django.conf.urls import include, url


app_name = 'staff'
from learning.views.gradebook import GradeBookCuratorDispatchView, \
    GradeBookTeacherView
from staff.views import HintListView, StudentSearchView, StudentSearchJSONView, \
    ExportsView, StudentsDiplomasStatsView, StudentsDiplomasView, \
    StudentsDiplomasCSVView, ProgressReportFullView, \
    ProgressReportForSemesterView, TotalStatisticsView, AdmissionReportView, \
    StudentFacesView, InterviewerFacesView, autograde_projects, \
    CourseParticipantsIntersectionView, SyllabusView

urlpatterns = [
    url(r'^syllabus/$', SyllabusView.as_view(), name='syllabus'),
    url(r'^warehouse/$', HintListView.as_view(), name='staff_warehouse'),
    url(r'^course-marks/$',
        GradeBookCuratorDispatchView.as_view(),
        name='course_markssheet_staff_dispatch'),
    url(r'^course-marks/(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
        GradeBookTeacherView.as_view(is_for_staff=True),
        name='course_markssheet_staff'),
    url(r'^student-search/$',
        StudentSearchView.as_view(),
        name='student_search'),
    url(r'^faces/interviewers/$',
        InterviewerFacesView.as_view(),
        name='interviewer_faces'),
    url(r'^faces/$',
        StudentFacesView.as_view(),
        name='student_faces'),
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
        url(r'^$',
            ExportsView.as_view(),
            name='exports'),
        url(r'^diplomas_stats/$',
            StudentsDiplomasStatsView.as_view(),
            name='exports_students_diplomas_stats'),
        url(r'^diplomas/$',
            StudentsDiplomasView.as_view(),
            name='exports_students_diplomas'),
        url(r'^diplomas/csv/$',
            StudentsDiplomasCSVView.as_view(),
            name='exports_students_diplomas_csv'),
        url(r'^sheet/csv/$',
            ProgressReportFullView.as_view(output_format="csv"),
            name='exports_sheet_all_students_csv'),
        url(r'^reports/admission/(?P<campaign_pk>\d+)/csv/$',
            AdmissionReportView.as_view(output_format="csv"),
            name='exports_report_admission_csv'),
        url(r'^reports/admission/(?P<campaign_pk>\d+)/xlsx/$',
            AdmissionReportView.as_view(output_format="xlsx"),
            name='exports_report_admission_xlsx'),
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

    # TODO: not implemented
    url(r'^statistics/csv/$',
        TotalStatisticsView.as_view(),
        name='total_statistics_csv'),
]


