from django.urls import path

from .views import ProjectPublicationView, RecordedEventView

urlpatterns = [
    path("projects/<slug:slug>/", ProjectPublicationView.as_view(), name="project_publication"),
    path("videos/<slug:slug>/", RecordedEventView.as_view(), name="recorded_event_detail"),

]
