from django.conf.urls import include
from django.urls import path

from admission.views import (
    ApplicantCreateStudentView, ApplicantDetailView, ApplicantListView,
    ApplicantStatusUpdateView, InterviewAssignmentDetailView, InterviewCommentView,
    InterviewDetailView, InterviewInvitationListView, InterviewInvitationCreateView,
    InterviewListView, InterviewResultsDispatchView, InterviewResultsView,
    import_campaign_testing_results
)

app_name = 'admission'

applicant_patterns = [
    path('', ApplicantListView.as_view(), name='list'),
    path('<int:pk>/', ApplicantDetailView.as_view(), name='detail'),
    path('<int:pk>/create_student', ApplicantCreateStudentView.as_view(), name='create_student'),
    path('status/<int:pk>/', ApplicantStatusUpdateView.as_view(), name='update_status'),
]

interview_invitation_patterns = [
    path('', InterviewInvitationListView.as_view(), name='list'),
    path('send', InterviewInvitationCreateView.as_view(), name='send'),
]

interview_patterns = [
    path('', InterviewListView.as_view(), name='list'),
    path('<int:pk>/', InterviewDetailView.as_view(), name='detail'),
    path('interviews/<int:pk>/comment', InterviewCommentView.as_view(), name='comment'),
    path('assignments/<int:pk>/', InterviewAssignmentDetailView.as_view(), name='assignment'),
]

results_patterns = [
    path('', InterviewResultsDispatchView.as_view(), name='dispatch'),
    path('<str:branch_code>/', InterviewResultsView.as_view(), name='list'),
]

urlpatterns = [
    path('admission/', include([
        path('<int:campaign_id>/testing/import/', import_campaign_testing_results, name='import_testing_results'),
        path('applicants/', include((applicant_patterns, 'applicants'))),
        path('interviews/', include(([
            path('', include(interview_patterns)),
            path('invitations/', include((interview_invitation_patterns, 'invitations'))),
        ], 'interviews'))),
        path('results/', include((results_patterns, 'results'))),
    ])),
]
