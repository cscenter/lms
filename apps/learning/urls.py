from django.conf.urls import include
from django.urls import path, re_path

from courses.urls import RE_COURSE_URI
from learning.study.views import UsefulListView, InternshipListView, \
    HonorCodeView
from .views import EventDetailView, CourseNewsNotificationUpdate, CourseStudentsView, InvitationView

urlpatterns = [
    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("students/", CourseStudentsView.as_view(), name="course_students"),
            path("news/notifications/", CourseNewsNotificationUpdate.as_view(), name="course_news_notifications_read"),
        ]), kwargs={"city_aware": True}),
        path('invitation/<str:token>/', InvitationView.as_view(), name="course_invitation"),
    ])),

    path('teaching/', include('learning.teaching.urls')),

    path('learning/', include('learning.study.urls')),
    path('learning/useful/', UsefulListView.as_view(), name='learning_useful'),
    path('learning/internships/', InternshipListView.as_view(), name='learning_internships'),
    path('learning/hc/', HonorCodeView.as_view(), name='honor_code'),
    path('learning/library/', include("library.urls")),

    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),
]
