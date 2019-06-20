from django.urls import path

from .views import ProjectPublicationView, OpenLectureView

urlpatterns = [
    path("projects/<slug:slug>/", ProjectPublicationView.as_view(), name="project_publication"),
    path("videos/<slug:slug>/", OpenLectureView.as_view(), name="open_lecture_detail"),

]
