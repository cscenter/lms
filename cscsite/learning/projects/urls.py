from django.conf.urls import include, url

from learning.projects.views import ReviewerProjectsView, ProjectDetailView, \
    ProjectEnrollView, ReportView, ReportAttachmentDownloadView, \
    ReportUpdateStatusView, ReportSummarizeView, StudentProjectsView

app_name = 'projects'
urlpatterns = [
    url(r'^learning/projects/$',
        StudentProjectsView.as_view(),
        name='student_projects'),
    url(r'^projects/', include([
        url(r'^$', ReviewerProjectsView.as_view(),
            name='reviewer_projects'),
        url(r'^(?P<pk>\d+)/$', ProjectDetailView.as_view(),
            name='project_detail'),
        url(r'^(?P<pk>\d+)/enroll$', ProjectEnrollView.as_view(),
            name='reviewer_project_enroll'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/status/',
            ReportUpdateStatusView.as_view(),
            name='project_report_update_status'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/summarize/',
            ReportSummarizeView.as_view(),
            name='project_report_summarize'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/',
            ReportView.as_view(),
            name='project_report'),
        url(r'^attachments/(?P<sid>[-\w]+)/$',
            ReportAttachmentDownloadView.as_view(),
            name='report_attachments_download'),
    ])),
]