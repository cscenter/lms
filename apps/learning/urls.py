from django.conf.urls import include
from django.urls import path, re_path

from courses.urls import RE_COURSE_URI
from learning.views import CourseInvitationEnrollView, ICalEventsView
from learning.study.views import UsefulListView, InternshipListView, HonorCodeView
from .views import EventDetailView, CourseNewsNotificationUpdate, \
    CourseStudentsView, CourseEnrollView, CourseUnenrollView

urlpatterns = [
    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("enroll/", CourseEnrollView.as_view(), name="course_enroll"),
            path("unenroll/", CourseUnenrollView.as_view(), name="course_leave"),
            path("enroll/invitation/<str:course_token>/", CourseInvitationEnrollView.as_view(), name="course_enroll_by_invitation"),
            path("students/", CourseStudentsView.as_view(), name="course_students"),
            path("news/notifications/", CourseNewsNotificationUpdate.as_view(), name="course_news_notifications_read"),
        ])),
    ])),

    path('teaching/', include('learning.teaching.urls')),

    path('learning/', include('learning.study.urls')),
    path('learning/useful/', UsefulListView.as_view(), name='learning_useful'),
    path('learning/internships/', InternshipListView.as_view(), name='learning_internships'),
    path('learning/hc/', HonorCodeView.as_view(), name='honor_code'),
    path('learning/library/', include("library.urls")),

    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),
    re_path(r'^csc_events.ics', ICalEventsView.as_view(), name='ical_events'),
]
