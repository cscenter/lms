from django.conf.urls import include
from django.urls import path, re_path

from courses.urls import RE_COURSE_URI
from learning.enrollment.views import CourseEnrollView, CourseUnenrollView

urlpatterns = [
    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("enroll", CourseEnrollView.as_view(), name="course_enroll"),
            path("unenroll", CourseUnenrollView.as_view(), name="course_leave"),
        ]), kwargs={"city_aware": True})
    ])),
]
