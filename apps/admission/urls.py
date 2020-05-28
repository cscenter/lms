from django.conf.urls import include, url
from django.urls import path

from admission.views import InterviewListView, InterviewDetailView, \
    ApplicantListView, ApplicantDetailView, \
    ApplicantStatusUpdateView, InterviewResultsView, ApplicantCreateUserView, \
    InterviewResultsDispatchView, InterviewAssignmentDetailView, \
    InterviewCommentView, InterviewAppointmentView, \
    InterviewAppointmentAssignmentsView, applicant_testing_new_task

app_name = 'admission'

urlpatterns = [
    url(r'^admission/', include([
        url(r'^applicants/$', ApplicantListView.as_view(), name='applicants'),
        url(r'^applicants/import/testing/$', applicant_testing_new_task, name='import_testing_results'),
        url(r'^applicants/(?P<pk>\d+)/$', ApplicantDetailView.as_view(), name='applicant_detail'),
        url(r'^applicants/(?P<pk>\d+)/create_user$', ApplicantCreateUserView.as_view(), name='applicant_create_user'),
        url(r'^applicants/status/(?P<pk>\d+)/$', ApplicantStatusUpdateView.as_view(), name='applicant_status_update'),
        url(r'^interviews/$', InterviewListView.as_view(), name='interviews'),
        url(r'^interviews/assignments/(?P<pk>\d+)/$', InterviewAssignmentDetailView.as_view(), name='interview_assignment_detail'),
        url(r'^interviews/(?P<pk>\d+)/$', InterviewDetailView.as_view(), name='interview_detail'),
        url(r'^interviews/(?P<pk>\d+)/comment$', InterviewCommentView.as_view(), name='interview_comment'),
        url(r'^results/$', InterviewResultsDispatchView.as_view(), name='interview_results_dispatch'),
        url(r'^results/(?P<branch_code>nsk|kzn|spb|distance|)/$', InterviewResultsView.as_view(), name='branch_interview_results'),
        url(r'^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/$', InterviewAppointmentView.as_view(), name='interview_appointment'),
        url(r'^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/assignments/$', InterviewAppointmentAssignmentsView.as_view(), name='interview_appointment_assignments')
    ])),
]
