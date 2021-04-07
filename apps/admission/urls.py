from django.conf.urls import include
from django.urls import re_path, path

from admission.views import InterviewListView, InterviewDetailView, \
    ApplicantListView, ApplicantDetailView, \
    ApplicantStatusUpdateView, InterviewResultsView, ApplicantCreateStudentView, \
    InterviewResultsDispatchView, InterviewAssignmentDetailView, \
    InterviewCommentView, import_campaign_testing_results

app_name = 'admission'

urlpatterns = [
    re_path(r'^admission/', include([
        path('applicants/', ApplicantListView.as_view(), name='applicants'),
        re_path(r'^applicants/(?P<pk>\d+)/$', ApplicantDetailView.as_view(), name='applicant_detail'),
        re_path(r'^applicants/(?P<pk>\d+)/create_student$', ApplicantCreateStudentView.as_view(), name='applicant_create_student'),
        path('applicants/import/<int:campaign_id>/testing/', import_campaign_testing_results, name='import_testing_results'),
        re_path(r'^applicants/status/(?P<pk>\d+)/$', ApplicantStatusUpdateView.as_view(), name='applicant_status_update'),
        re_path(r'^interviews/$', InterviewListView.as_view(), name='interviews'),
        re_path(r'^interviews/assignments/(?P<pk>\d+)/$', InterviewAssignmentDetailView.as_view(), name='interview_assignment_detail'),
        re_path(r'^interviews/(?P<pk>\d+)/$', InterviewDetailView.as_view(), name='interview_detail'),
        re_path(r'^interviews/(?P<pk>\d+)/comment$', InterviewCommentView.as_view(), name='interview_comment'),
        re_path(r'^results/$', InterviewResultsDispatchView.as_view(), name='interview_results_dispatch'),
        re_path(r'^results/(?P<branch_code>\w+)/$', InterviewResultsView.as_view(), name='branch_interview_results'),
    ])),
]
