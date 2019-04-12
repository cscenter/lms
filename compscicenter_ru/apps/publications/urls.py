from django.conf.urls import include
from django.urls import path

from .views import ProjectPublicationView

urlpatterns = [
    path("projects/", include([
        path("<slug:slug>/", ProjectPublicationView.as_view(), name="project_publication"),
    ]))
]
