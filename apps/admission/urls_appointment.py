from django.conf.urls import include, url

from admission import views as v

app_name = 'appointment'

urlpatterns = [
    url(r'^admission/', include([
        url(r'^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/$', v.InterviewAppointmentView.as_view(), name='choosing_interview_date'),
        url(r'^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/assignments/$', v.InterviewAppointmentAssignmentsView.as_view(), name='interview_assignments')
    ])),
]
