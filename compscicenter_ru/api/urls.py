from django.urls import include, path

from application.api.views import ApplicantCreateAPIView
from publications.api.views import RecordedEventList

from . import views as v

app_name = 'public-api'

urlpatterns = [
    path('v2/', include(([
        path('applicants/', ApplicantCreateAPIView.as_view(), name='applicant_create'),
        path('alumni/', v.AlumniList.as_view(), name='alumni'),
        path('courses/', v.CourseList.as_view(), name='course_list'),
        path('courses/videos/', v.CourseVideoList.as_view(), name='course_videos'),
        path('recorded-events/videos/', RecordedEventList.as_view(), name='recorded_events_videos'),
        path('teachers/', v.TeacherList.as_view(), name='teachers'),
        path('teachers/courses/', v.SiteCourseList.as_view(), name='teachers_meta_courses'),
        path('testimonials/', v.TestimonialList.as_view(), name='testimonials'),
    ], 'v2')))
]
