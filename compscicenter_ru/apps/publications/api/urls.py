from django.urls import path

from . import views as v

urlpatterns = [
    path('recorded-events/videos/', v.RecordedEventList.as_view(), name='recorded_events_videos'),
]
