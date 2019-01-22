from django.conf.urls import include
from django.urls import path, re_path

from courses.urls import RE_COURSE_URI
from learning.views import CourseNewsUnreadNotificationsView, CourseStudentsView
from .views import EventDetailView

urlpatterns = [
    path('', include('learning.enrollment.urls')),
    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("students/", CourseStudentsView.as_view(), name="course_students"),
            path("news/", include([
                path("<int:news_pk>/stats", CourseNewsUnreadNotificationsView.as_view(), name="course_news_unread"),
            ])),
        ]), kwargs={"city_aware": True})
    ])),

    path('learning/', include('learning.studying.urls')),

    path('teaching/', include('learning.teaching.urls')),

    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),
]
