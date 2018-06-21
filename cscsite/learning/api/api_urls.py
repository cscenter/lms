from django.conf.urls import url

from . import views as v

urlpatterns = [
        url(r'^alumni/$', v.AlumniList.as_view(), name='alumni'),
        url(r'^testimonials/$', v.TestimonialList.as_view(),
            name='testimonials'),
]
