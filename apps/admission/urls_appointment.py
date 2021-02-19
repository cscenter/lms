from django.urls import re_path, path, include

from admission import views as v

app_name = 'appointment'

urlpatterns = [
    path('admission/', include([
        re_path(r'^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/$', v.InterviewAppointmentView.as_view(), name='choosing_interview_date'),
        re_path(r'^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/assignments/$', v.InterviewAppointmentAssignmentsView.as_view(), name='interview_assignments')
    ])),
]
