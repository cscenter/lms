from django.conf.urls import include, url

from admission.views import InterviewListView, InterviewDetailView, \
    ApplicantListView, ApplicantDetailView, \
    ApplicantStatusUpdateView, InterviewResultsView, ApplicantCreateStudentView, \
    InterviewResultsDispatchView, InterviewAssignmentDetailView, \
    InterviewCommentView, applicant_testing_new_task

app_name = 'admission'

urlpatterns = [
    url(r'^admission/', include([
        url(r'^applicants/$', ApplicantListView.as_view(), name='applicants'),
        url(r'^applicants/import/testing/$', applicant_testing_new_task, name='import_testing_results'),
        url(r'^applicants/(?P<pk>\d+)/$', ApplicantDetailView.as_view(), name='applicant_detail'),
        url(r'^applicants/(?P<pk>\d+)/create_student$', ApplicantCreateStudentView.as_view(), name='applicant_create_student'),
        url(r'^applicants/status/(?P<pk>\d+)/$', ApplicantStatusUpdateView.as_view(), name='applicant_status_update'),
        url(r'^interviews/$', InterviewListView.as_view(), name='interviews'),
        url(r'^interviews/assignments/(?P<pk>\d+)/$', InterviewAssignmentDetailView.as_view(), name='interview_assignment_detail'),
        url(r'^interviews/(?P<pk>\d+)/$', InterviewDetailView.as_view(), name='interview_detail'),
        url(r'^interviews/(?P<pk>\d+)/comment$', InterviewCommentView.as_view(), name='interview_comment'),
        url(r'^results/$', InterviewResultsDispatchView.as_view(), name='interview_results_dispatch'),
        url(r'^results/(?P<branch_code>\w+)/$', InterviewResultsView.as_view(), name='branch_interview_results'),
    ])),
]
