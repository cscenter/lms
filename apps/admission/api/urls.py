from django.urls import include, path, re_path

from . import views as v

app_name = 'admission-api'

urlpatterns = [
    path('v2/', include(([
        path('interviews/slots/', v.InterviewSlots.as_view(), name='interview_slots'),
    ], 'v2')))
]
