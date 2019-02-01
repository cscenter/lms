from django.conf.urls import include
from django.urls import path

from learning.projects import views

app_name = 'projects'

urlpatterns = [
    path('projects/', include([
        path('reports/', views.ReportListReviewerView.as_view(), name='report_list_reviewers'),
        path('reports-all/', views.ReportListCuratorView.as_view(), name='report_list_curators'),
        path('available/', views.CurrentTermProjectsView.as_view(), name='current_term_projects'),
        path('all/', views.ProjectListView.as_view(), name='all_projects'),
        path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
        path('<int:pk>/results', views.ProjectResultsView.as_view(), name='project_results_update'),
        path('<int:pk>/enroll', views.ProjectEnrollView.as_view(), name='reviewer_project_enroll'),
        path('<int:project_pk>/report/<int:student_pk>/status/', views.ReportUpdateStatusView.as_view(), name='project_report_update_status'),
        path('<int:project_pk>/report/<int:student_pk>/curator_assess/', views.ReportCuratorAssessmentView.as_view(), name='project_report_curator_assessment'),
        path('<int:project_pk>/report/<int:student_pk>/summarize/', views.ReportCuratorSummarizeView.as_view(), name='project_report_summarize'),
        path('<int:project_pk>/report/<int:student_pk>/', views.ReportView.as_view(), name='project_report'),
        path('prev/<int:project_id>)/', views.ProjectPrevNextView.as_view(direction="prev"), name='project_detail_prev'),
        path('next/<int:project_id>/', views.ProjectPrevNextView.as_view(direction="next"), name='project_detail_next'),
        path('attachments/<str:sid>/', views.ReportAttachmentDownloadView.as_view(), name='report_attachments_download'),
    ])),
    path('learning/projects/', include([
        path('', views.StudentProjectsView.as_view(), name='student_projects'),
        path('<int:pk>/', views.ProjectDetailView.as_view(), name='student_project_detail'),
        path('<int:project_pk>/report/<int:student_pk>/', views.ReportView.as_view(), name='student_project_report'),
    ])),
]
