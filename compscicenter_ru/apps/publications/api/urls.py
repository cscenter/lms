from django.urls import path

from . import views as v

urlpatterns = [
    path('open-lectures/videos/', v.OpenLectureVideoList.as_view(), name='open_lecture_video_records'),
]
