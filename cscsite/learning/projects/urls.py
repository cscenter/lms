from django.conf.urls import include, url

from learning.projects.views import ProjectDetailView, \
    ProjectEnrollView, ReportView, ReportAttachmentDownloadView, \
    ReportUpdateStatusView, ReportCuratorSummarizeView, StudentProjectsView, \
    ReportCuratorAssessmentView, ProjectPrevNextView, ReportListReviewerView, \
    CurrentTermProjectsView, ProjectListView, ReportListCuratorView, \
    ProjectResultsView

app_name = 'projects'
urlpatterns = [
    url(r'^projects/', include([
        url(r'^reports/$', ReportListReviewerView.as_view(),
            name='report_list_reviewers'),
        url(r'^reports-all/$', ReportListCuratorView.as_view(),
            name='report_list_curators'),
        url(r'^available/$', CurrentTermProjectsView.as_view(),
            name='current_term_projects'),
        url(r'^all/$', ProjectListView.as_view(),
            name='all_projects'),
        url(r'^(?P<pk>\d+)/$', ProjectDetailView.as_view(),
            name='project_detail'),
        url(r'^prev/(?P<project_id>\d+)/$',
            ProjectPrevNextView.as_view(direction="prev"),
            name='project_detail_prev'),
        url(r'^(?P<pk>\d+)/results$', ProjectResultsView.as_view(),
            name='project_results_update'),
        url(r'^next/(?P<project_id>\d+)/$',
            ProjectPrevNextView.as_view(direction="next"),
            name='project_detail_next'),
        url(r'^(?P<pk>\d+)/enroll$', ProjectEnrollView.as_view(),
            name='reviewer_project_enroll'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/status/',
            ReportUpdateStatusView.as_view(),
            name='project_report_update_status'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/curator_assess/',
            ReportCuratorAssessmentView.as_view(),
            name='project_report_curator_assessment'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/summarize/',
            ReportCuratorSummarizeView.as_view(),
            name='project_report_summarize'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/',
            ReportView.as_view(),
            name='project_report'),
        url(r'^attachments/(?P<sid>[-\w]+)/$',
            ReportAttachmentDownloadView.as_view(),
            name='report_attachments_download'),
    ])),

    url(r'^learning/projects/', include([
        url(r'^$', StudentProjectsView.as_view(),
            name='student_projects'),
        url(r'^(?P<pk>\d+)/$', ProjectDetailView.as_view(),
            name='student_project_detail'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/',
            ReportView.as_view(),
            name='student_project_report'),
    ])),
]
