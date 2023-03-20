from django.urls import include, path, re_path

from admission import views as v
from admission.api.views import (
    AppointmentInterviewCreateApi,
    AppointmentInterviewInvitationApi,
)

app_name = "appointment"

api_urls = [
    re_path(
        r"^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/$",
        AppointmentInterviewInvitationApi.as_view(),
        name="interview_appointment",
    ),
    re_path(
        r"^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/(?P<slot_id>\d+)/$",
        AppointmentInterviewCreateApi.as_view(),
        name="interview_appointment_slots",
    ),
]

urlpatterns = [
    path(
        "admission/",
        include(
            [
                re_path(
                    r"^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/$",
                    v.InterviewAppointmentView.as_view(),
                    name="select_time_slot",
                ),
                re_path(
                    r"^appointment/(?P<year>\d{4})/(?P<secret_code>\w+)/assignments/$",
                    v.InterviewAppointmentAssignmentsView.as_view(),
                    name="interview_assignments",
                ),
            ]
        ),
    ),
    path("api/v1/", include((api_urls, "api"))),
]
