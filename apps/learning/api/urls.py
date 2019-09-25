from django.urls import path, include

from . import views as v

app_name = 'api'

urlpatterns = [
    path('v2/', include(([
        path('alumni/', v.AlumniList.as_view(), name='alumni'),
        path('testimonials/', v.TestimonialList.as_view(), name='testimonials'),
    ], 'v2')))
]
