from django.conf.urls import include, url

from learning.admission.views import InterviewListView, InterviewDetailView, \
    ApplicantListView, ApplicantDetailView, \
    ApplicantStatusUpdateView, InterviewResultsView, ApplicantCreateUserView, \
    InterviewResultsDispatchView, ApplicantRequestWizardView, \
    ApplicationCompleteView, InterviewAssignmentDetailView, \
    InterviewCommentView, InterviewAppointmentView, InterviewSlots

urlpatterns = [
    url(r'^admission/', include([
        url(r'^applicants/$', ApplicantListView.as_view(), name='admission_applicants'),
        url(r'^applicants/(?P<pk>\d+)/$', ApplicantDetailView.as_view(), name='admission_applicant_detail'),
        url(r'^applicants/(?P<pk>\d+)/create_user$', ApplicantCreateUserView.as_view(), name='admission_applicant_create_user'),
        url(r'^applicants/status/(?P<pk>\d+)/$', ApplicantStatusUpdateView.as_view(), name='admission_applicant_status_update'),
        url(r'^interviews/$', InterviewListView.as_view(), name='admission_interviews'),
        url(r'^interviews/slots/$', InterviewSlots.as_view(), name='admission_interview_slots'),
        url(r'^interviews/assignments/(?P<pk>\d+)$', InterviewAssignmentDetailView.as_view(), name='admission_interview_assignment_detail'),
        url(r'^interviews/(?P<pk>\d+)$', InterviewDetailView.as_view(), name='admission_interview_detail'),
        url(r'^interviews/(?P<pk>\d+)/comment$', InterviewCommentView.as_view(), name='admission_interview_comment'),
        url(r'^results/$', InterviewResultsDispatchView.as_view(), name='admission_interview_results_dispatch'),
        url(r'^results/(?P<city_slug>\w+)/$', InterviewResultsView.as_view(), name='admission_interview_results_by_city'),
        url(r'^appointment/(?P<date>\d{2}\.\d{2}\.\d{4})/(?P<secret_code>\w+)/$',
            InterviewAppointmentView.as_view(),
            name='admission_interview_appointment'),
    ])),
]
