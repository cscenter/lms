from django.urls import path

from .views import ProjectPublicationView, RecordedEventView, ProjectsListView, \
    ProjectPracticeView, ProjectResearchWorkView

urlpatterns = [
    path('projects/', ProjectsListView.as_view(), name="public_projects"),
    path('projects-practice/', ProjectPracticeView.as_view(), name="project_practice"),
    path('projects-research/', ProjectResearchWorkView.as_view(), name="project_research"),
    path("projects/<slug:slug>/", ProjectPublicationView.as_view(), name="project_publication"),
    path("videos/<slug:slug>/", RecordedEventView.as_view(), name="recorded_event_detail"),

]
