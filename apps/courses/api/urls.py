from django.urls import path

from . import views as v

urlpatterns = [
    path('courses/', v.CourseList.as_view(), name='courses'),
    path('courses/videos/', v.CourseVideoList.as_view(), name='course_video_records'),
    path('teachers/', v.TeacherList.as_view(), name='teachers'),
]
