from django.conf.urls import url

from . import views as v

urlpatterns = [
        url(r'^alumni/$', v.AlumniList.as_view(), name='api_alumni'),
]
