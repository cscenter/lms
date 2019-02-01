from django.conf.urls import include
from django.urls import path, re_path

from courses.urls import RE_COURSE_URI
from learning.teaching.views import CourseStudentsView
from .views import EventDetailView

urlpatterns = [
    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("students/", CourseStudentsView.as_view(), name="course_students"),
        ]), kwargs={"city_aware": True})
    ])),

    path('learning/', include('learning.study.urls')),

    path('teaching/', include('learning.teaching.urls')),

    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),
]
