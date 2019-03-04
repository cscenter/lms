from django.conf.urls import url

from . import views as v

urlpatterns = [
    url(r'^courses/$', v.CourseList.as_view(), name='courses'),
    url(r'^courses/videos/$', v.CourseVideoList.as_view(), name='course_video_records'),
    url(r'^teachers/$', v.TeacherList.as_view(), name='teachers'),
]
