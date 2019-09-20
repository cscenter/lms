from django.conf.urls import include
from django.urls import path

from projects import views

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
        path('<int:project_pk>/reports/<int:report_id>/', include([
            path('', views.ReportView.as_view(), name='project_report'),
            path('update/', views.ReportUpdateStatusView.as_view(), name='project_report_update'),
            path('curator_assess/', views.ReportCuratorAssessmentView.as_view(), name='project_report_curator_assessment'),
            path('summarize/', views.ReportCuratorSummarizeView.as_view(), name='project_report_summarize'),
            path('review/', views.ProcessReviewFormView.as_view(), name='project_report_upsert_review'),
            path('comments/<int:comment_id>/update/', views.ReportCommentUpdateView.as_view(), name='report_comment_edit'),
        ])),
        path('prev/<int:project_id>)/', views.ProjectPrevNextView.as_view(direction="prev"), name='project_detail_prev'),
        path('next/<int:project_id>/', views.ProjectPrevNextView.as_view(direction="next"), name='project_detail_next'),
        path('attachments/<str:sid>/', views.ReportAttachmentDownloadView.as_view(), name='report_attachments_download'),
    ])),
    path('learning/projects/', include([
        path('', views.StudentProjectsView.as_view(), name='student_projects'),
        path('<int:pk>/', views.ProjectDetailView.as_view(), name='study__project_detail'),
        path('<int:project_pk>/report/<int:report_id>/', views.ReportView.as_view(), name='student_project_report'),
    ])),
]
