from django.conf.urls import include, url

from learning.projects.views import ReviewerProjectsView, ProjectDetailView, \
    ProjectEnrollView, ReviewerReportView, ReportAttachmentDownloadView

app_name = 'projects'
urlpatterns = [
    url(r'^projects/', include([
        url(r'^$', ReviewerProjectsView.as_view(),
            name='reviewer_projects'),
        url(r'^(?P<pk>\d+)/$', ProjectDetailView.as_view(),
            name='reviewer_project_detail'),
        url(r'^(?P<pk>\d+)/enroll$', ProjectEnrollView.as_view(),
            name='reviewer_project_enroll'),
        url(r'^(?P<project_pk>\d+)/report/(?P<student_pk>\d+)/',
            ReviewerReportView.as_view(),
            name='reviewer_project_report'),
        url(r'^attachments/(?P<sid>[-\w]+)/$',
            ReportAttachmentDownloadView.as_view(),
            name='report_attachments_download'),
    ])),
]