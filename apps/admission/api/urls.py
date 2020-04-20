from django.urls import path, include

from . import views as v

app_name = 'admission-api'

urlpatterns = [
    path('v2/', include(([
        path('interviews/slots/', v.InterviewSlots.as_view(), name='interview_slots'),
    ], 'v2')))
]
