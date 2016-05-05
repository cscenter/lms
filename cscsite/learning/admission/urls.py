from django.conf.urls import include, url

from learning.admission.views import InterviewListView, InterviewDetailView, \
    ApplicantResultsListView, ApplicantResultsDetailView, \
    ApplicantStatusUpdateView

urlpatterns = [
    url(r'^admission', include([
        url(r'^/applicants/$', ApplicantResultsListView.as_view(), name='admission_applicants'),
        url(r'^/applicants/(?P<pk>\d+)/$', ApplicantResultsDetailView.as_view(), name='admission_applicant_detail'),
        url(r'^/applicants/status/(?P<pk>\d+)/$', ApplicantStatusUpdateView.as_view(), name='admission_applicant_status_update'),
        url(r'^/interviews/$', InterviewListView.as_view(), name='admission_dashboard'),
        url(r'^/interviews/(?P<pk>\d+)$', InterviewDetailView.as_view(), name='admission_interview_detail'),
    ])),
]