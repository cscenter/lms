from django.conf.urls import include
from django.urls import path

from admission.views import (
    ApplicantCreateStudentView, ApplicantDetailView, ApplicantListView,
    ApplicantStatusUpdateView, InterviewAssignmentDetailView, InterviewCommentView,
    InterviewDetailView, InterviewListView, InterviewResultsDispatchView,
    InterviewResultsView, SendInvitationListView, StatusInvitationListView,
    import_campaign_testing_results
)

app_name = 'admission'

applicant_patterns = [
    path('', ApplicantListView.as_view(), name='list'),
    path('<int:pk>/', ApplicantDetailView.as_view(), name='detail'),
    path('<int:pk>/create_student', ApplicantCreateStudentView.as_view(), name='create_student'),
    path('status/<int:pk>/', ApplicantStatusUpdateView.as_view(), name='update_status'),
]

interview_patterns = [
    path('', InterviewListView.as_view(), name='list'),
    path('<int:pk>/', InterviewDetailView.as_view(), name='detail'),
    path('interviews/<int:pk>/comment', InterviewCommentView.as_view(), name='comment'),
    path('assignments/<int:pk>/', InterviewAssignmentDetailView.as_view(), name='assignment'),
]

results_patterns = [
    path('results/', InterviewResultsDispatchView.as_view(), name='dispatch'),
    path('results/<str:branch_code>/', InterviewResultsView.as_view(), name='list'),
]

urlpatterns = [
    path('admission/', include([
        path('<int:campaign_id>/testing/import/', import_campaign_testing_results, name='import_testing_results'),
        path('applicants/', include((applicant_patterns, 'applicants'))),
        path('interviews/', include((interview_patterns, 'interviews'))),
        path('results/', include((results_patterns, 'results'))),
        path('interviews/invitations/add/', SendInvitationListView.as_view(), name='send_interview_invitations'),
        path('status_invitations/', StatusInvitationListView.as_view(), name='status_interview_invitations'),
    ])),
]
